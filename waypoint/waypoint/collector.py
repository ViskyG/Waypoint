"""Foreground observer: same live IPC + persisted rollouts, one normalized sink.

No Codex launch/turn/approval operation. Reconnects on failed delivery and re-reads
from committed JSONL cursors. Run as the same OS user as the explicitly selected
existing Codex session. Real-target acceptance remains an installation step.
"""
from __future__ import annotations
import fcntl
import json
import os
import time
import uuid
from pathlib import Path
from urllib.parse import quote, urlencode
from .adapters.codex import JsonlTail, Normalizer, discover_family
from .adapters.ipc import Follower
from .client import Client, Unavailable
from .domain import ContractError, canonical, digest, now

ROLLOUT_NORMALIZATION_VERSION = 3

def event_batches(events):
    batch, size = [], 0
    for event in events:
        event_size = len(canonical(event).encode())
        if batch and (len(batch) >= 200 or size + event_size > 7_000_000):
            yield batch
            batch, size = [], 0
        batch.append(event)
        size += event_size
    if batch:
        yield batch


class Collector:
    def __init__(self, client: Client, project: str, root_thread: str, ipc: Path, rollouts: Path, max_frame: int = 32 * 1024 * 1024, coalesce_seconds: float | None = None):
        self.client, self.project, self.thread = client, project, root_thread
        self.ipc, self.root, self.max_frame = ipc, rollouts, max_frame
        self.path = "/api/p/" + quote(project, safe="")
        self.family = {}
        self.ipc_source = "codex-ipc/" + digest(root_thread)[:12]
        self.rollout_source = "codex-rollout/" + digest(root_thread)[:12]
        self.norm = Normalizer(project, self.ipc_source)
        self.norms: dict[str, Normalizer] = {}
        self.pending: dict[str, dict] = {}
        self.committed: dict[str, dict] = {}
        self.coalesce_seconds = float(os.environ.get("WP_COALESCE_MS", "200")) / 1000 if coalesce_seconds is None else coalesce_seconds
        if not 0 <= self.coalesce_seconds <= 5:
            raise ContractError("coalescing", "Coalescing interval must be between zero and five seconds")
        self.last_health = 0.0
        self._rollout_health = None
        self.issues = set()
        self.started_at = now()

    def health(self, state: str, detail: str, source: str | None = None):
        source = source or self.ipc_source
        event = {"event_id": uuid.uuid4().hex, "project_id": self.project, "source": source, "kind": "source.health", "at": now(), "payload": {"source_key": source, "state": state, "detail": detail, "root_thread": self.thread}}
        self.client.call("POST", self.path + "/events", {"events": [event]})
        if source == self.rollout_source:
            self._rollout_health = state
        self.last_health = time.monotonic()

    def snapshot(self, thread: str, state: dict, historical: bool, change: dict | None = None):
        if "batches" in self.pending.get(thread, {}):
            self.flush(thread, force=True)
        source_key = "ipc:" + self.project + ":" + thread
        if thread not in self.norms:
            saved = self.client.call("GET", "/api/cursor?" + urlencode({"source_key": source_key})) or {}
            self.committed[thread] = saved
            self.norms[thread] = Normalizer(self.project, self.ipc_source, saved.get("generation"))
        normalizer = self.norm = self.norms[thread]
        events = normalizer.snapshot(state, thread, historical, change, source_key)
        pending = self.pending.setdefault(thread, {"events": {}, "deadline": time.monotonic() + self.coalesce_seconds})
        pending["revision"] = (change or {}).get("revision")
        pending["source_key"] = source_key
        for event in events:
            payload = event["payload"]
            key = (event["kind"], payload.get("item_id"), payload.get("detail"))
            pending["events"][key] = event
        terminal = any(e["kind"] == "item.upsert" and str(e["payload"].get("state", "")).lower() in {"completed", "complete", "failed", "cancelled", "canceled", "interrupted", "done", "error"} for e in events)
        idle = any(e["kind"] == "agent.activity" and e["payload"].get("state") in {"idle", "completed", "failed"} for e in events)
        if historical or terminal or idle or self.coalesce_seconds == 0:
            self.flush(thread, force=True)

    def flush(self, thread: str | None = None, force: bool = False):
        """Acknowledge only after every batch and the final durable barrier."""
        for native in list(self.pending) if thread is None else [thread]:
            pending = self.pending.get(native)
            if pending is None or (not force and time.monotonic() < pending["deadline"]):
                continue
            normalizer = self.norms[native]
            revision, source_key = pending["revision"], pending["source_key"]
            # Keep the exact prepared bodies on delivery failure for idempotent retry.
            if "batches" not in pending:
                begin = normalizer.event("source.health", {"source_key": source_key, "state": "hydrating", "detail": "revision_pending", "root_thread": self.thread}, native)
                end = normalizer.event("source.health", {"source_key": source_key, "state": "connected", "detail": "revision_committed", "root_thread": self.thread, "committed_revision": revision, "generation": normalizer.generation}, native)
                batches = list(event_batches([begin, *pending["events"].values(), end]))
                pending["batches"] = batches
                pending["next_batch"] = 0
            batches = pending["batches"]
            previous = self.committed[native].get("revision")
            for index in range(pending["next_batch"], len(batches)):
                final = index == len(batches) - 1
                cursor = {"source_key": source_key, "project_id": self.project, "native_id": native, "generation": normalizer.generation, "revision": revision if final else previous, "received_revision": revision, "hydrating": not final}
                self.client.call("POST", self.path + "/events", {"events": batches[index], "cursor": cursor})
                pending["next_batch"] = index + 1
                if final:
                    self.committed[native] = cursor
            del self.pending[native]

    def tail_once(self):
        had_issue = False
        for native, (meta, path) in list(self.family.items()):
            source_key = "rollout:" + self.project + ":" + digest(str(path.resolve()))[:32]
            saved = self.client.call("GET", "/api/cursor?" + urlencode({"source_key": source_key})) or {}
            if saved.get("normalization_version") != ROLLOUT_NORMALIZATION_VERSION:
                # Replay only this selected source under the expanded mapping.
                # Preserve generation/source locations: previous evidence retries
                # identically; newly supported native events append to the ledger.
                saved = {**saved, "offset": 0, "fork_context": {"active_native": native, "restored": False}}
            reader = JsonlTail(path, saved)
            rows, cursor = reader.read(150)
            cursor["source_key"] = source_key
            normalizer = Normalizer(self.project, self.rollout_source, reader.generation)
            context = dict(saved.get("fork_context") or {"active_native": native, "restored": False})
            identity = context.get("active_native")
            fork_parent = meta.get("forked_from_id")
            events = []
            for key, row in rows:
                # Records predating this collector are history, never today's focus.
                timestamp = row.get("timestamp", "")
                historical = not timestamp or timestamp < self.started_at
                payload = row.get("payload", {})
                if not isinstance(payload, dict):
                    continue
                if fork_parent:
                    if row.get("type") == "session_meta":
                        reported = payload.get("id")
                        identity = reported if reported == native or (reported == fork_parent and reported in self.family) else None
                        context.update(active_native=identity, restored=False)
                    elif row.get("type") == "event_msg" and payload.get("type") == "thread_settings_applied":
                        # Inspect identity only, never the settings body. The
                        # actual native marker separates copied fork history
                        # from this verified executor's own subsequent records.
                        reported = payload.get("thread_id")
                        identity = reported if reported == native or (reported == fork_parent and reported in self.family) else None
                        context.update(active_native=identity, restored=reported == native)
                        continue
                    if identity is None:
                        continue  # Unproven copied identity stays quarantined.
                receipt_identity = key + ":native:" + native if fork_parent and context.get("restored") and identity == native else None
                identity, emitted = normalizer.rollout(row, identity, key, historical, receipt_identity)
                events.extend(emitted)
            context["active_native"] = identity
            cursor["native_id"] = native
            cursor["fork_context"] = context
            cursor["normalization_version"] = ROLLOUT_NORMALIZATION_VERSION
            if rows or reader.issue:
                batches = list(event_batches(events)) or [[]]
                for index, batch in enumerate(batches):
                    body = {"events": batch}
                    if index == len(batches) - 1:
                        body["cursor"] = cursor
                    self.client.call("POST", self.path + "/events", body)
            if reader.issue:
                had_issue = True
                self.health("gap", reader.issue, self.rollout_source)
        # Clear a persisted gap only after every selected source was actually
        # read and its receipts committed. Ordinary successful rounds are quiet.
        # IPC health remains independent and previous gap events stay immutable.
        if self.family and not had_issue and self._rollout_health != "connected":
            self.health("connected", "Selected-family rollout round committed", self.rollout_source)

    def run(self, duration: float | None = None):
        lock_path = self.client.directory / ("collector-" + digest([self.project, self.thread])[:16] + ".lock")
        with lock_path.open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ContractError("collector_active", "A collector already observes this project/root") from exc
            self._loop(duration)

    def _loop(self, duration):
        started = time.monotonic()
        follower = None
        next_connect = next_scan = next_tail = 0.0
        backoff = 1.0
        while duration is None or time.monotonic() - started < duration:
            try:
                t = time.monotonic()
                if t >= next_scan:
                    self.family = discover_family(self.root, self.thread)
                    self.issues.clear()
                    next_scan = t + 30
                if t >= next_tail:
                    try:
                        self.tail_once()
                    except (OSError, ContractError) as exc:
                        self.health("gap", getattr(exc, "code", type(exc).__name__), self.rollout_source)
                    next_tail = t + 0.25
                if follower is None and t >= next_connect:
                    self.flush(force=True)
                    follower = Follower(self.ipc, self.snapshot, self.health, self.max_frame, on_change=self.snapshot)
                    follower.connect()
                    follower.follow(self.thread)
                    backoff = 1
                if follower is not None:
                    # Only the selected root's proven descendants; absent live owner
                    # is not an error about the historical child's existence.
                    for native in set(self.family) - set(follower.owners):
                        if native in self.issues:
                            continue
                        try:
                            follower.follow(native)
                        except ContractError as exc:
                            if exc.code in {"owner_missing", "ipc_reply"}:
                                self.issues.add(native)
                            else:
                                raise
                    follower.pump(0.05)
                    follower.resync()
                    self.flush()
                    if t - self.last_health >= 10:
                        self.health("connected", "Connection present; silence is not agent completion")
                else:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                break
            except (OSError, ConnectionError, ContractError, KeyError, ValueError) as exc:
                if follower is not None:
                    follower.close()
                    follower = None
                try:
                    self.health("disconnected", getattr(exc, "code", type(exc).__name__))
                except (Unavailable, ContractError):
                    pass  # source reconnect + committed cursor replay, never fake success
                next_connect = time.monotonic() + backoff
                backoff = min(backoff * 2, 30)
                time.sleep(min(backoff, 1))
        if follower is not None:
            follower.close()
        try:
            self.flush(force=True)
            self.health("stopped", "Observer stopped; agents were not stopped")
        except (Unavailable, ContractError):
            pass
