"""Pure contracts, validation and conservative three-way plan merge.

Status text is deliberately not an enum. Structural validation protects storage;
it does not decide what work an agent may perform.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@/\-]{0,199}$")
MISSING = object()
MAX_TEXT = 2_000_000
MAX_NODES = 20_000  # protective input bound, not a claimed rendering capacity


class ContractError(ValueError):
    def __init__(self, code: str, message: str, detail: Any = None):
        super().__init__(message)
        self.code, self.detail = code, detail

    def as_dict(self) -> dict:
        return {"error": self.code, "message": str(self), "detail": self.detail}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def ident(value: Any, field: str) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ContractError("invalid_id", f"Invalid {field}")
    return value


def text(value: Any, field: str, maximum: int = MAX_TEXT) -> str:
    if not isinstance(value, str) or len(value) > maximum:
        raise ContractError("invalid_text", f"{field} must be text <= {maximum} characters")
    return value


def _records(value: Any, field: str, limit: int = MAX_NODES) -> dict:
    if not isinstance(value, dict) or len(value) > limit:
        raise ContractError("invalid_collection", f"{field} must be a bounded dictionary")
    for key, record in value.items():
        ident(key, field + " key")
        if not isinstance(record, dict):
            raise ContractError("invalid_record", f"{field}/{key} must be an object")
    return value


def ancestors(plan: dict, node_id: str) -> list[str]:
    result, seen = [], set()
    current = node_id
    while current and current in plan["nodes"] and current not in seen:
        result.append(current)
        seen.add(current)
        current = plan["nodes"][current].get("parent")
    return result


def descendants(plan: dict, node_id: str) -> set[str]:
    result = {node_id}
    children: dict[str, list[str]] = {}
    for key, node in plan["nodes"].items():
        children.setdefault(node.get("parent"), []).append(key)
    pending = [node_id]
    while pending:
        for child in children.get(pending.pop(), []):
            if child not in result:
                result.add(child)
                pending.append(child)
    return result


def validate_plan(value: Any) -> tuple[dict, list[dict]]:
    """Return a detached normalized plan and warnings. No status-derived gates."""
    if not isinstance(value, dict) or value.get("schema") != "waypoint.plan/1":
        raise ContractError("schema", "Expected waypoint.plan/1")
    plan = copy.deepcopy(value)
    ident(plan.get("project_id"), "project_id")
    if "/" in plan["project_id"]:
        raise ContractError("project_id", "project_id must be a single URL path segment")
    text(plan.get("title"), "title", 500)
    nodes = _records(plan.get("nodes"), "nodes")
    edges = _records(plan.get("edges", {}), "edges", 100_000)
    plan["edges"] = edges
    for key, node in nodes.items():
        parent = node.get("parent")
        if parent is not None and (not isinstance(parent, str) or parent not in nodes):
            raise ContractError("missing_parent", f"Unknown parent for {key}")
    for key, node in nodes.items():
        text(node.get("title"), f"{key}.title", 500)
        text(node.get("assignment", ""), f"{key}.assignment")
        node.setdefault("assignment", "")
        node.setdefault("parent", None)
        if node["parent"] is not None and node["parent"] not in nodes:
            raise ContractError("missing_parent", f"Unknown parent for {key}")
        for collection in ("acceptance", "tests"):
            entries = node.setdefault(collection, {})
            _records(entries, f"{key}.{collection}", 10_000)
            for eid, entry in entries.items():
                text(entry.get("text", entry.get("label", "")), f"{key}/{eid}", 50_000)
        layout = node.setdefault("layout", {})
        if not isinstance(layout, dict):
            raise ContractError("layout", "layout must be an object")
        for coord in ("x", "y", "lane", "depth"):
            if coord in layout and (isinstance(layout[coord], bool) or not isinstance(layout[coord], (int, float)) or not math.isfinite(layout[coord]) or abs(layout[coord]) > 1_000_000):
                raise ContractError("layout", f"Invalid {key} layout coordinate")
        current, seen = key, set()
        while current:
            if current in seen:
                raise ContractError("parent_cycle", f"Nesting cycle through {key}")
            seen.add(current)
            current = nodes[current].get("parent")
    adjacency: dict[str, set[str]] = {key: set() for key in nodes}
    indegree = {key: 0 for key in nodes}
    for key, edge in edges.items():
        for endpoint in ("from", "to"):
            if edge.get(endpoint) not in nodes:
                raise ContractError("missing_endpoint", f"{key}.{endpoint} does not exist")
        if edge["to"] not in adjacency[edge["from"]]:
            adjacency[edge["from"]].add(edge["to"])
            indegree[edge["to"]] += 1
    queue = [key for key in nodes if indegree[key] == 0]
    visited = 0
    while queue:
        key = queue.pop()
        visited += 1
        for nxt in adjacency[key]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    warnings = []
    if visited != len(nodes):
        warnings.append({"code": "dependency_cycle", "message": "Dependency graph is cyclic; displayed, not enforced", "affected_or_downstream": [key for key, degree in indegree.items() if degree]})
    canonical(plan)  # Reject NaN or non-JSON content even in extensions.
    return plan, warnings


def three_way(base: Any, current: Any, proposed: Any, path: tuple[str, ...] = ()) -> tuple[Any, list[dict]]:
    """Merge disjoint dictionary fields. Lists are atomic. Preserve delete conflicts."""
    if proposed == base:
        return copy.deepcopy(current) if current is not MISSING else MISSING, []
    if current == base or current == proposed:
        return copy.deepcopy(proposed) if proposed is not MISSING else MISSING, []
    if isinstance(base, dict) and isinstance(current, dict) and isinstance(proposed, dict):
        merged, conflicts = {}, []
        for key in sorted(set(base) | set(current) | set(proposed)):
            item, bad = three_way(base.get(key, MISSING), current.get(key, MISSING), proposed.get(key, MISSING), path + (key,))
            conflicts.extend(bad)
            if item is not MISSING:
                merged[key] = item
        return merged, conflicts
    def safe(v):
        return {"absent": True} if v is MISSING else v
    return current, [{"path": list(path), "base": safe(base), "current": safe(current), "proposed": safe(proposed)}]


def plan_diff(before: Any, after: Any, path: tuple[str, ...] = ()) -> list[dict]:
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        changes = []
        for key in sorted(set(before) | set(after)):
            changes.extend(plan_diff(before.get(key, MISSING), after.get(key, MISSING), path + (key,)))
        return changes
    change = {"path": list(path), "op": "add" if before is MISSING else "remove" if after is MISSING else "replace"}
    if before is not MISSING:
        change["before"] = before
    if after is not MISSING:
        change["after"] = after
    return [change]


def validate_event(value: Any, project: str | None = None) -> dict:
    if not isinstance(value, dict) or value.get("schema", "waypoint.event/1") != "waypoint.event/1":
        raise ContractError("schema", "Expected waypoint.event/1")
    event = copy.deepcopy(value)
    event.setdefault("schema", "waypoint.event/1")
    for field in ("event_id", "project_id", "source", "kind"):
        ident(event.get(field), field)
    if "/" in event["project_id"]:
        raise ContractError("project_id", "project_id must be a single URL path segment")
    if project is not None and event["project_id"] != project:
        raise ContractError("project_mismatch", "Event is for another project")
    if event.get("agent_id") is not None:
        ident(event["agent_id"], "agent_id")
    if "at" not in event:
        raise ContractError("timestamp", "at is required; stamp once before retrying")
    try:
        ts = datetime.fromisoformat(event["at"].replace("Z", "+00:00"))
        if ts.tzinfo is None:
            raise ValueError("Timezone required")
        event["at"] = ts.astimezone(timezone.utc).isoformat(timespec="microseconds")
    except (ValueError, TypeError, AttributeError):
        raise ContractError("timestamp", "at must be an ISO timestamp with timezone")
    for field in ("node_ids", "edge_ids"):
        refs = event.setdefault(field, [])
        if not isinstance(refs, list) or len(refs) > 1000 or any(not isinstance(x, str) or not ID.fullmatch(x) for x in refs):
            raise ContractError("references", f"Invalid {field}")
        event[field] = list(dict.fromkeys(refs))
    payload = event.setdefault("payload", {})
    if not isinstance(payload, dict):
        raise ContractError("payload", "payload must be an object")
    if event["kind"] in {"scope.set", "agent.upsert", "agent.activity", "item.upsert", "item.link"} and not event.get("agent_id"):
        raise ContractError("agent_required", "This event requires a distinct agent_id")
    if event["kind"] in {"node.status", "node.result", "test.result"} and not event["node_ids"]:
        raise ContractError("node_required", "This event requires at least one node reference")
    if event["kind"] == "node.status":
        text(payload.get("status"), "status", 240)
        text(payload.get("explanation", ""), "explanation")
    if event["kind"] in {"item.upsert", "item.link"}:
        ident(payload.get("item_id"), "item_id")
    if event["kind"] == "item.upsert":
        text(payload.get("text", ""), "text")
        text(payload.get("type", "message"), "type", 100)
    if event["kind"] == "test.result":
        ident(payload.get("test_id"), "test_id")
        ident(payload.get("run_id"), "run_id")
        if payload.get("outcome") not in {"passed", "failed", "skipped", "error", "not_run"}:
            raise ContractError("outcome", "Invalid test outcome")
        if payload.get("freshness", "unknown") not in {"current", "stale", "unknown"}:
            raise ContractError("freshness", "Invalid freshness declaration")
        if payload.get("freshness") == "current" and not payload.get("basis"):
            raise ContractError("basis_required", "Current evidence needs an explicit basis")
    if len(canonical(event).encode()) > 3_000_000:
        raise ContractError("event_too_large", "Normalized event exceeds 3 MB")
    return event
