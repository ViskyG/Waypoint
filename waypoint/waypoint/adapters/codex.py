"""Normalize provider-visible Codex data; no inference or settings/auth collection."""
from __future__ import annotations
import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any, Iterator
from ..domain import ContractError, canonical, digest, now

ITEM_TYPES = {"agentMessage", "userMessage", "reasoning", "commandExecution", "mcpToolCall", "fileChange", "subAgentActivity"}
HISTORY_ROOTS = (("turns",), ("turnHistory", "history", "entitiesByKey"))
PRIVATE_BRANCHES = {"arguments", "input", "output", "instructions", "encrypted_content"}


def at_path(state: Any, path: tuple) -> Any:
    try:
        for key in path:
            state = state[key]
        return state
    except (KeyError, IndexError, TypeError):
        return None


class ItemIndex:
    """Index only history containers. Normal text changes visit one indexed item."""
    def __init__(self):
        self.items: dict[tuple, str] = {}
        self.below: dict[tuple, set[tuple]] = {}
        self.first_revision: dict[str, int | None] = {}
        self.work = {"visited": 0, "normalized": 0, "rebuilds": 0}

    def rebuild(self, state: dict, prefix: tuple, revision: int | None):
        old = list(self.below.get(prefix, ()))
        for path in old:
            self.items.pop(path, None)
            for depth in range(len(path) + 1):
                members = self.below.get(path[:depth])
                if members is not None:
                    members.discard(path)
                    if not members:
                        self.below.pop(path[:depth], None)
        stack = [(prefix, at_path(state, prefix))]
        self.work["rebuilds"] += 1
        while stack:
            path, current = stack.pop()
            self.work["visited"] += 1
            if self.work["visited"] > 100_000 or len(path) > 128:
                raise ContractError("state_size", "History subtree exceeds configured traversal/depth budget")
            if isinstance(current, dict):
                if current.get("type") in ITEM_TYPES and current.get("id"):
                    ident = str(current["id"])
                    self.items[path] = ident
                    self.first_revision.setdefault(ident, revision)
                    for depth in range(len(path) + 1):
                        self.below.setdefault(path[:depth], set()).add(path)
                    continue
                stack.extend((path + (k,), v) for k, v in current.items() if isinstance(v, (dict, list)) and k not in PRIVATE_BRANCHES)
            elif isinstance(current, list):
                stack.extend((path + (i,), v) for i, v in reversed(list(enumerate(current))))

    def update(self, state: dict, change: dict | None) -> tuple[set[tuple], list[tuple]]:
        self.work = {"visited": 0, "normalized": 0, "rebuilds": 0}
        revision = (change or {}).get("revision")
        if change is None or change.get("type") == "snapshot" or not self.items:
            for root in HISTORY_ROOTS:
                self.rebuild(state, root, revision)
            return set(self.items), []
        dirty, rebuild, diagnostics = set(), set(), []
        for patch in change.get("patches", []):
            path = tuple(patch["path"])
            ancestors = [r for r in HISTORY_ROOTS if len(path) < len(r) and r[:len(path)] == path]
            if ancestors:
                rebuild.update(ancestors)
                continue
            root = next((r for r in HISTORY_ROOTS if path[:len(r)] == r or r[:len(path)] == path), None)
            if root is None:
                continue
            item = next((path[:d] for d in range(len(path), 0, -1) if path[:d] in self.items), None)
            if item is not None and path != item and path[len(item)] not in {"id", "type"}:
                dirty.add(item)
                continue
            # Array insert/remove shifts sibling indices: rebuild that container.
            if path and isinstance(path[-1], int) and patch["op"] in {"add", "remove"}:
                subtree = path[:-1]
            elif item is not None:
                subtree = item
            elif path in self.below or path == root:
                subtree = path
            elif path and path[:-1] in self.below and patch["op"] == "add":
                subtree = path
            else:
                subtree = root
                diagnostics.append(root)
            rebuild.add(subtree if len(subtree) >= len(root) else root)
        # Drop nested invalidations if their ancestor is already rebuilt.
        roots = [p for p in rebuild if not any(p != q and p[:len(q)] == q for q in rebuild)]
        for root in roots:
            self.rebuild(state, root, revision)
            dirty.update(self.below.get(root, ()))
        return {p for p in dirty if p in self.items}, diagnostics


def agent_key(native_id: str) -> str:
    return "codex/" + native_id


def executor_metadata(meta: dict) -> dict:
    """Observed persisted thread_spawn fields; distinct payload.id stays primary."""
    source = meta.get("source")
    subagent = source.get("subagent") if isinstance(source, dict) else None
    spawn = subagent.get("thread_spawn") if isinstance(subagent, dict) else None
    return {**(spawn if isinstance(spawn, dict) else {}), **meta}


def readable(value: Any) -> str:
    """Extract available text, never decrypt or invent missing reasoning."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(filter(None, (readable(v) for v in value)))
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        if "content" in value:
            return readable(value["content"])
    return ""


def item_text(item: dict) -> str:
    kind = item.get("type", "")
    kind = kind[:1].lower() + kind[1:]
    if kind == "reasoning":
        return readable(item.get("summary")) or readable(item.get("summary_text")) or readable(item.get("content")) or readable(item.get("raw_content"))
    if kind == "commandExecution":
        return "\n".join(v for v in [readable(item.get("command")), readable(item.get("aggregatedOutput"))] if v)
    if kind == "fileChange":
        return readable(item.get("text")) or canonical(item.get("changes", []))
    if kind == "mcpToolCall":
        parts = [str(item.get("server", "")), str(item.get("tool", item.get("name", "")))]
        output = readable(item.get("result")) or readable(item.get("output"))
        return " ".join(filter(None, parts)) + ("\n" + output if output else "")
    return readable(item.get("text")) or readable(item.get("content"))


def bounded_content(content: str, limit: int = 1_900_000) -> tuple[str, bool]:
    """Bound serialized UTF-8 bytes, including JSON escaping, below event cap."""
    original = len(content)
    content = content.encode()[:limit].decode("utf-8", errors="ignore")
    while (size := len(canonical(content).encode())) > limit:
        content = content[:max(0, int(len(content) * limit / size) - 1)]
    return content, len(content) != original


def walk_items(state: dict, limit: int = 100_000) -> Iterator[dict]:
    # Only known conversation-history roots; never walk latestThreadSettings,
    # developer instructions, credentials, arbitrary tool argument trees, etc.
    roots = [state.get("turns", []), state.get("turnHistory", {}).get("history", {}).get("entitiesByKey", {})]
    stack, seen_ids, visited = list(roots), set(), 0
    while stack:
        current = stack.pop()
        visited += 1
        if visited > limit:
            raise ContractError("state_size", "Conversation traversal exceeds configured budget")
        if isinstance(current, dict):
            kind = current.get("type", "")
            native_id = current.get("id")
            if kind in ITEM_TYPES and native_id:
                if native_id not in seen_ids:
                    seen_ids.add(native_id)
                    yield current
                # Do not mistake tool output content for nested real agent items.
                continue
            stack.extend(v for k, v in current.items() if isinstance(v, (dict, list)) and k not in {"arguments", "input", "output", "instructions", "encrypted_content"})
        elif isinstance(current, list):
            stack.extend(reversed(current))


class Normalizer:
    def __init__(self, project: str, source: str, generation: str | None = None):
        self.project, self.source = project, source
        self.generation = generation or uuid.uuid4().hex
        self.hashes: dict[tuple[str, str], str] = {}
        self.indexes: dict[str, ItemIndex] = {}
        self.last_work: dict = {}
        self.ordinal = 0

    def event(self, kind: str, payload: dict, native_agent: str | None, at: str | None = None, identity: str | None = None) -> dict:
        self.ordinal += 1
        key = identity or str(self.ordinal)
        observed_at = at or now()
        # Recreated observers retain the committed source generation, but their
        # local ordinal restarts. A fresh local observation has a fresh timestamp
        # and identity; a prepared delivery retry retains this exact event body.
        # Explicit persisted record identities keep their existing stable hash.
        if identity is None and at is None:
            key = [key, observed_at]
        return {"schema": "waypoint.event/1", "event_id": digest([self.project, self.source, self.generation, key, kind, payload]), "project_id": self.project, "source": self.source, "kind": kind, "agent_id": agent_key(native_agent) if native_agent else None, "at": observed_at, "node_ids": [], "edge_ids": [], "payload": payload}

    def metadata(self, meta: dict, at: str | None = None, identity: str | None = None) -> dict:
        meta = executor_metadata(meta)
        native = meta.get("id")
        if not isinstance(native, str) or not native:
            raise ContractError("native_id", "session_meta.payload.id is required; session_id is not a replacement")
        body = {"provider": "codex"}
        if meta.get("agentNickname") or meta.get("agent_nickname") or meta.get("agent_path"):
            body["name"] = meta.get("agentNickname") or meta.get("agent_nickname") or meta.get("agent_path")
        for dest, candidates in {"parent_id": ("parent_thread_id", "parentThreadId"), "session_id": ("session_id", "sessionId"), "agent_path": ("agent_path",), "forked_from_id": ("forked_from_id", "forkedFromId"), "cwd": ("cwd",)}.items():
            for key in candidates:
                if key in meta:
                    val = meta[key]
                    if val is not None:
                        body[dest] = agent_key(val) if dest == "parent_id" else val
                    break
        return self.event("agent.upsert", body, native, at, identity)

    def snapshot(self, state: dict, native: str, historical: bool = False, change: dict | None = None, source_key: str | None = None) -> list[dict]:
        if state.get("id") not in {None, native}:
            raise ContractError("thread_mismatch", "Snapshot belongs to a different thread")
        result = [self.metadata({**state, "id": native})]
        runtime = state.get("threadRuntimeStatus")
        activity = runtime.get("type") if isinstance(runtime, dict) else None
        if isinstance(activity, str) and activity:
            result.append(self.event("agent.activity", {"state": {"active": "running", "idle": "idle"}.get(activity, activity), "reported_by": "threadRuntimeStatus"}, native))
        index = self.indexes.setdefault(native, ItemIndex())
        dirty, diagnostics = index.update(state, change)
        revision = (change or {}).get("revision")
        for root in diagnostics:
            result.append(self.event("source.health", {"source_key": source_key or self.source, "state": "rebuilding", "detail": "unknown_history_structure", "root": list(root)}, native))
        seen = set()
        for path in sorted(dirty, key=repr):
            item = at_path(state, path)
            if not isinstance(item, dict) or item.get("type") not in ITEM_TYPES or not item.get("id"):
                continue
            ident = str(item["id"])
            if ident in seen:
                continue
            seen.add(ident)
            index.work["normalized"] += 1
            fingerprint = digest(item)
            if self.hashes.get((native, ident)) == fingerprint:
                continue
            content = item_text(item)
            # This is a local content cap, always reported rather than silent.
            content, truncated = bounded_content(content)
            payload = {"item_id": ident, "native_item_id": ident, "turn_id": item.get("turnId"), "type": item["type"], "text": content, "state": item.get("status", "observed"), "historical": historical, "truncated": truncated}
            if revision is not None:
                payload.update(source_key=source_key or self.source, source_revision=revision, source_first_revision=index.first_revision.get(ident, revision), source_generation=self.generation)
            if item["type"] == "subAgentActivity":
                for field in ("kind", "agent_thread_id", "agent_path"):
                    if isinstance(item.get(field), str):
                        payload[field] = item[field]
            if item["type"] == "reasoning":
                payload["content_origin"] = "provider_summary" if readable(item.get("summary")) or readable(item.get("summary_text")) else "provider_visible_text"
                if not content:
                    continue  # encrypted-only reasoning is not exposed/reconstructed
            result.append(self.event("item.upsert", payload, native))
            self.hashes[(native, ident)] = fingerprint
        self.last_work = dict(index.work)
        return result

    def rollout(self, event: dict, native: str | None, record_key: str, historical: bool = True, event_identity: str | None = None) -> tuple[str | None, list[dict]]:
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            return native, []
        at = event.get("timestamp") or "1970-01-01T00:00:00+00:00"  # stable unknown-time sentinel, never a fabricated live time
        receipt_identity = event_identity or record_key
        if event.get("type") == "session_meta":
            native = payload.get("id")
            return native, [self.metadata(payload, at, receipt_identity)]
        if not native:
            return native, []
        kind = payload.get("type")
        if event.get("type") == "event_msg" and kind in {"task_started", "task_complete"}:
            # These are observations of this native thread's own turn. A turn
            # completing reports idle, never an inferred agent/plan completion.
            body = {"state": "running" if kind == "task_started" else "idle", "reported_by": "event_msg." + kind, "turn_id": payload.get("turn_id"), "historical": historical}
            return native, [self.event("agent.activity", body, native, at, receipt_identity)]
        if event.get("type") == "event_msg" and kind in {"item_completed", "item_started"}:
            item = payload.get("item", {})
            native_id = item.get("id")
            typ = item.get("type", "")
            typ = typ[:1].lower() + typ[1:]
            if native_id and typ in ITEM_TYPES:
                normalized = {**item, "type": typ}
                content = item_text(normalized)
                if typ == "reasoning" and not content:
                    return native, []
                content, truncated = bounded_content(content)
                body = {"item_id": str(native_id), "native_item_id": native_id, "turn_id": payload.get("turn_id"), "type": typ, "text": content, "state": item.get("status", "completed" if kind == "item_completed" else "running"), "historical": historical, "truncated": truncated}
                if typ == "subAgentActivity":
                    for field in ("kind", "agent_thread_id", "agent_path"):
                        if isinstance(item.get(field), str):
                            body[field] = item[field]
                if typ == "reasoning":
                    body["content_origin"] = "provider_summary" if readable(item.get("summary")) or readable(item.get("summary_text")) else "provider_visible_text"
                return native, [self.event("item.upsert", body, native, at, receipt_identity)]
        if event.get("type") == "response_item" and kind == "message":
            role = payload.get("role")
            if role not in {"assistant", "user"}:
                return native, []
            # Without a proven native ID, use source location, not message hash.
            ident = payload.get("id") or "rollout:" + hashlib.sha256(record_key.encode()).hexdigest()[:32]
            content, truncated = bounded_content(readable(payload.get("content")))
            body = {"item_id": ident, "type": "agentMessage" if role == "assistant" else "userMessage", "text": content, "state": "observed", "historical": historical, "truncated": truncated, "identity_quality": "native" if payload.get("id") else "source_location"}
            return native, [self.event("item.upsert", body, native, at, receipt_identity)]
        return native, []


class JsonlTail:
    """Read complete lines only. Cursors are committed by the consumer with events."""
    def __init__(self, path: Path, cursor: dict | None = None, max_line: int = 3_000_000):
        self.path = path
        self.offset = int((cursor or {}).get("offset", 0))
        self.file_identity = (cursor or {}).get("file_identity")
        self.generation = (cursor or {}).get("generation")
        self.prefix_length = int((cursor or {}).get("prefix_length", 0))
        self.prefix_hash = (cursor or {}).get("prefix_hash")
        self.native_id = (cursor or {}).get("native_id")
        self.max_line = max_line
        self.issue = None

    def read(self, limit: int = 250) -> tuple[list[tuple[str, dict]], dict]:
        saved = self.__dict__.copy()
        try:
            return self._read(limit)
        except Exception:
            self.__dict__.update(saved)
            raise

    def _read(self, limit: int) -> tuple[list[tuple[str, dict]], dict]:
        stat = self.path.stat()
        identity = f"{stat.st_dev}:{stat.st_ino}"
        reset = self.file_identity not in {None, identity} or stat.st_size < self.offset
        with self.path.open("rb") as f:
            if self.prefix_length and self.prefix_hash:
                observed = hashlib.sha256(f.read(self.prefix_length)).hexdigest()
                reset = reset or observed != self.prefix_hash
            if reset:
                self.generation, self.offset = None, 0
                self.prefix_length, self.prefix_hash = 0, None
                self.issue = "source_generation_changed"
            self.file_identity = identity
            if not self.prefix_length and stat.st_size:
                f.seek(0)
                prefix = f.read(min(4096, stat.st_size))
                self.prefix_length = len(prefix)
                self.prefix_hash = hashlib.sha256(prefix).hexdigest()
            if not self.generation:
                self.generation = digest([str(self.path.resolve()), identity, self.prefix_hash])[:32]
            f.seek(self.offset)
            rows = []
            for _ in range(limit):
                start = f.tell()
                line = f.readline(self.max_line + 1)
                if len(line) > self.max_line:
                    raise ContractError("rollout_line_size", "Rollout line too large; cursor not advanced")
                if not line or not line.endswith(b"\n"):
                    break
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict):
                        raise ValueError("not an object")
                except ValueError:
                    # Do not consume corrupt data as if it were processed.
                    raise ContractError("rollout_json", "Malformed complete JSONL record; cursor preserved")
                self.offset = f.tell()
                key = f"{identity}:{self.generation}:{start}"
                rows.append((key, event))
        cursor = {"source_key": "rollout:" + str(self.path.resolve()), "offset": self.offset, "file_identity": identity, "generation": self.generation, "prefix_length": self.prefix_length, "prefix_hash": self.prefix_hash, "native_id": self.native_id}
        return rows, cursor


def discover_family(root: Path, root_thread: str) -> dict[str, tuple[dict, Path]]:
    """Read first-line metadata only; return the selected family, not every chat."""
    records = {}
    for path in root.rglob("*.jsonl"):
        try:
            if path.is_symlink():
                continue
            with path.open("rb") as f:
                line = f.readline(3_000_001)
            if len(line) > 3_000_000:
                continue
            entry = json.loads(line)
            meta = entry.get("payload", {})
            if entry.get("type") == "session_meta" and isinstance(meta, dict) and meta.get("id"):
                records[meta["id"]] = (executor_metadata(meta), path)
        except (OSError, ValueError):
            continue
    selected, changed = {root_thread}, True
    while changed:
        changed = False
        for ident, (meta, _) in records.items():
            if meta.get("parent_thread_id") in selected and ident not in selected:
                selected.add(ident); changed = True
    return {k: v for k, v in records.items() if k in selected}
