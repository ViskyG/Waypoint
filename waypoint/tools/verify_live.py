#!/usr/bin/env python3
"""Compare selected actual Codex family against Waypoint without exporting text.

Read-only toward both systems. Unrelated rollout files are read only for their
first-line metadata. This is target evidence, never a synthetic test fixture.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import platform
import socket
import sqlite3
import stat
import struct
import time
from pathlib import Path


def text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(filter(None, (text(v) for v in value)))
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        return text(value.get("content"))
    return ""


def original_text(item, kind):
    if kind in {"agentMessage", "userMessage"}:
        return text(item.get("text")) or text(item.get("content"))
    if kind == "reasoning":
        return text(item.get("summary")) or text(item.get("summary_text")) or text(item.get("content")) or text(item.get("raw_content"))
    if kind == "commandExecution":
        return "\n".join(filter(None, [text(item.get("command")), text(item.get("aggregatedOutput"))]))
    # Message and command strings have direct, independently inspectable provider
    # fields. Other types are counted but excluded from exact-text assertions.
    return None


def ipc_snapshot(path, root):
    """One bounded read-only owner hydration; keep original snapshot in memory."""
    info = path.stat()
    if info.st_uid != os.getuid() or not stat.S_ISSOCK(info.st_mode):
        raise ValueError("IPC socket owner/type mismatch")
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.settimeout(3)
    client = "waypoint-verifier"
    owner = None
    sequence = 0
    methods = []
    pending = bytearray()
    responses = {}
    snapshots = []
    observation = {"subscription_cleanup_sent": False, "connection_closed": False}

    def send(message):
        method = message.get("method", message["type"])
        if method not in {"initialize", "thread-owner-discovery", "thread-follower-load-complete-history", "thread-stream-following-changed", "client-discovery-response"}:
            raise ValueError("Disallowed verification RPC")
        encoded = json.dumps(message).encode()
        connection.sendall(struct.pack("<I", len(encoded)) + encoded)
        methods.append(method)

    def receive():
        chunk = connection.recv(1_048_576)
        if not chunk:
            raise ConnectionError("IPC closed")
        pending.extend(chunk)
        while len(pending) >= 4:
            size = struct.unpack("<I", pending[:4])[0]
            if not 0 < size <= 45 * 1024 * 1024:
                raise ValueError("IPC frame size out of bounds")
            if len(pending) < size + 4:
                break
            message = json.loads(pending[4:4 + size])
            del pending[:4 + size]
            if message.get("type") == "response":
                responses[message.get("requestId")] = message
            elif message.get("type") == "client-discovery-request":
                send({"type": "client-discovery-response", "requestId": message["requestId"], "response": {"canHandle": False}})
            elif message.get("type") == "broadcast" and message.get("method") == "thread-stream-state-changed":
                params = message.get("params", {})
                change = params.get("change", {})
                if params.get("conversationId") == root and change.get("type") == "snapshot":
                    snapshots.append((change.get("conversationState", {}), size))

    def rpc(method, params, version=0, target=None):
        nonlocal sequence
        sequence += 1
        rid = "verify-live-" + str(sequence)
        message = {"type": "request", "requestId": rid, "sourceClientId": client, "version": version, "method": method, "params": params, "timeoutMs": 3000}
        if target:
            message["targetClientId"] = target
        send(message)
        deadline = time.monotonic() + 4
        while rid not in responses and time.monotonic() < deadline:
            receive()
        response = responses.pop(rid, {})
        if response.get("resultType") != "success":
            raise ValueError("Read-only owner RPC unsuccessful: " + method)
        return response

    def following(value):
        send({"type": "broadcast", "method": "thread-stream-following-changed", "sourceClientId": client, "targetClientIds": [owner], "version": 1, "params": {"hostId": "local", "conversationId": root, "following": value}})

    try:
        connection.connect(str(path))
        if hasattr(socket, "SO_PEERCRED"):
            _, uid, _ = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid != os.getuid():
                raise ValueError("IPC peer owner mismatch")
        client = rpc("initialize", {"clientType": "waypoint-readonly-verifier"})["result"]["clientId"]
        owner = rpc("thread-owner-discovery", {"hostId": "local", "conversationId": root}, 1).get("handledByClientId")
        if not owner:
            raise ValueError("Actual owner not found")
        following(True)
        rpc("thread-follower-load-complete-history", {"conversationId": root}, 1, owner)
        deadline = time.monotonic() + 4
        while not snapshots and time.monotonic() < deadline:
            receive()
        if not snapshots:
            raise ValueError("No actual owner snapshot received")
        observation.update({"owner_found": True, "methods": sorted(set(methods)), "snapshot_frame_bytes": snapshots[-1][1], "snapshot_samples": len(snapshots), "source_control_commands": 0})
        return snapshots[-1][0], observation
    finally:
        if owner:
            try:
                following(False)
                observation["subscription_cleanup_sent"] = True
            except OSError:
                pass
        connection.close()
        observation["connection_closed"] = True


def compare_ipc(state, database, project, root):
    source = {}
    stack = [state.get("turns", []), state.get("turnHistory", {}).get("history", {}).get("entitiesByKey", {})]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            kind = value.get("type")
            if value.get("id") and kind in {"agentMessage", "userMessage", "commandExecution", "reasoning", "mcpToolCall", "fileChange", "subAgentActivity"}:
                source[value["id"]] = (kind, original_text(value, kind), value.get("status"))
                continue
            stack.extend(v for k, v in value.items() if k not in {"arguments", "input", "output", "instructions", "encrypted_content"} and isinstance(v, (dict, list)))
        elif isinstance(value, list):
            stack.extend(value)
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as db:
        projected = {ident: json.loads(body) for ident, body in db.execute("SELECT id,body FROM items WHERE project=? AND agent=?", (project, "codex/" + root))}
    equal, missing, unequal, types, excluded, native_equal, inflight = [collections.Counter() for _ in range(7)]
    for ident, (kind, original, status) in source.items():
        types[kind] += 1
        if kind == "reasoning" and not original:
            excluded["reasoning_without_provider_visible_text"] += 1
            continue
        actual = projected.get(ident)
        if actual is None:
            missing[kind] += 1
        elif actual.get("type") != kind:
            unequal["type"] += 1
        else:
            native_equal[kind] += 1
            if kind == "commandExecution" and str(status).lower() not in {"completed", "failed", "interrupted", "cancelled", "canceled", "done", "declined"}:
                inflight[kind] += 1
            elif original is not None:
                (equal if actual.get("text") == original else unequal)[kind] += 1
    return {"source_item_types": dict(types), "native_id_type_equal": dict(native_equal), "native_id_type_original_text_equal": dict(equal), "not_yet_projected": dict(missing), "unequal": dict(unequal), "excluded_without_visible_text": dict(excluded), "inflight_command_text_excluded": dict(inflight), "exact_comparison_scope": "provider-visible messages, reasoning and terminal command text; other types compare native identity/type only"}


def selected_family(directory, root):
    records = {}
    for path in directory.rglob("*.jsonl"):
        if path.is_symlink():
            continue
        try:
            with path.open("rb") as stream:
                line = stream.readline(3_000_001)
            if len(line) > 3_000_000:
                continue
            row = json.loads(line)
            meta = row.get("payload", {})
            if row.get("type") == "session_meta" and meta.get("id"):
                records[meta["id"]] = (meta, path)
        except (OSError, ValueError):
            continue
    family = {root}
    while True:
        added = set()
        for native, (meta, _) in records.items():
            source = meta.get("source", {})
            spawn = source.get("subagent", {}).get("thread_spawn", {}) if isinstance(source, dict) else {}
            parent = meta.get("parent_thread_id") or spawn.get("parent_thread_id")
            if parent in family:
                added.add(native)
        if added <= family:
            return {native: records[native] for native in family if native in records}
        family |= added


def compare(database, project, family):
    actual = {}
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as db:
        for agent, ident, body in db.execute("SELECT agent,id,body FROM items WHERE project=?", (project,)):
            actual[(agent.removeprefix("codex/"), ident)] = json.loads(body)
        agents = {ident.removeprefix("codex/"): json.loads(body) for ident, body in db.execute("SELECT id,body FROM agents WHERE project=?", (project,))}
        cursor_rows = [json.loads(row[0]) for row in db.execute("SELECT body FROM cursors")]
        source_health = [json.loads(row[0]) for row in db.execute("SELECT body FROM source_health WHERE project=?", (project,))]
        duplicates = db.execute("SELECT COUNT(*) FROM (SELECT agent,id,COUNT(*) n FROM items WHERE project=? GROUP BY agent,id HAVING n>1)", (project,)).fetchone()[0]
    latest = {}
    lifecycle = {}
    source_types = collections.Counter()
    bytes_read = 0
    for native, (_, path) in family.items():
        observed_native = native
        with path.open("rb") as stream:
            for raw in stream:
                bytes_read += len(raw)
                if not raw.endswith(b"\n"):
                    break
                try:
                    row = json.loads(raw)
                except ValueError:
                    continue
                payload = row.get("payload", {})
                if row.get("type") == "session_meta" and payload.get("id") in family:
                    observed_native = payload["id"]
                if row.get("type") == "event_msg" and payload.get("type") == "thread_settings_applied" and payload.get("thread_id") in family:
                    # Only the explicit identity marker is read; settings stay
                    # uninspected. Forks contain an inherited parent prefix.
                    observed_native = payload["thread_id"]
                if row.get("type") == "event_msg" and payload.get("type") in {"task_started", "task_complete"}:
                    at = row.get("timestamp", "")
                    if at >= lifecycle.get(observed_native, ("", ""))[0]:
                        lifecycle[observed_native] = (at, "running" if payload["type"] == "task_started" else "idle")
                if row.get("type") != "event_msg" or payload.get("type") != "item_completed":
                    continue
                item = payload.get("item", {})
                kind = item.get("type", "")
                kind = kind[:1].lower() + kind[1:]
                if item.get("id"):
                    source_types[kind] += 1
                    latest[(observed_native, str(item["id"]))] = (kind, original_text(item, kind), item)
    matched = collections.Counter()
    missing = collections.Counter()
    unequal = collections.Counter()
    excluded = collections.Counter()
    unsupported = collections.Counter()
    native_equal = collections.Counter()
    subagent_metadata_equal = 0
    for key, (kind, original, item) in latest.items():
        if kind not in {"agentMessage", "userMessage", "commandExecution", "reasoning", "fileChange", "mcpToolCall", "subAgentActivity"}:
            unsupported[kind] += 1
            continue
        if kind == "reasoning" and not original:
            excluded["reasoning_without_provider_visible_text"] += 1
            continue
        projected = actual.get(key)
        if projected is None:
            missing[kind] += 1
            continue
        if projected.get("type") != kind:
            unequal["type"] += 1
        else:
            native_equal[kind] += 1
            if kind == "subAgentActivity":
                if all(projected.get(field) == item.get(field) for field in ("kind", "agent_thread_id", "agent_path")) and projected.get("text") == "":
                    subagent_metadata_equal += 1
                else:
                    unequal["subAgentActivity_metadata"] += 1
            if original is not None:
                if projected.get("text") == original:
                    matched[kind] += 1
                else:
                    unequal[kind] += 1
    genealogy = 0
    for native, (meta, _) in family.items():
        source = meta.get("source", {})
        spawn = source.get("subagent", {}).get("thread_spawn", {}) if isinstance(source, dict) else {}
        parent = meta.get("parent_thread_id") or spawn.get("parent_thread_id")
        if parent and agents.get(native, {}).get("parent_id") == "codex/" + parent:
            genealogy += 1
    native_cursors = [c for c in cursor_rows if "revision" in c]
    activity = collections.Counter()
    lifecycle_equal = collections.Counter()
    lifecycle_unequal = collections.Counter()
    provenance = collections.Counter()
    cursor_native_equal = cursor_native_unequal = 0
    for native in family:
        record = agents.get(native, {})
        if record:
            historical = "unobserved" if not record.get("activity_at") else ("historical" if record.get("activity_historical") else "current")
            provenance[historical + ":" + str(record.get("activity_reported_by", "unknown"))] += 1
        if native in lifecycle and record:
            expected = lifecycle[native][1]
            (lifecycle_equal if record.get("activity") == expected else lifecycle_unequal)[expected] += 1
        if str(record.get("activity_source", "")).startswith("codex-ipc/"):
            activity[record.get("activity", "unknown")] += 1
        _, path = family[native]
        source_key = "rollout:" + project + ":" + hashlib.sha256(json.dumps(str(path.resolve()), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:32]
        cursor = next((c for c in cursor_rows if c.get("source_key") == source_key), None)
        if cursor:
            if cursor.get("native_id") == native:
                cursor_native_equal += 1
            else:
                cursor_native_unequal += 1
    extension_versions = []
    for base in (Path.home() / ".vscode/extensions", Path.home() / ".vscode-insiders/extensions"):
        for manifest in base.glob("openai.chatgpt-*/package.json"):
            try:
                extension_versions.append(json.loads(manifest.read_text())["version"])
            except (OSError, ValueError, KeyError):
                continue
    return {
        "evidence": "actual_selected_owner_rollout_compared_to_current_waypoint_database",
        "family_count": len(family), "family_agents_projected": sum(native in agents for native in family),
        "genealogy_edges_equal": genealogy, "source_complete_native_items_by_type": dict(source_types),
        "native_id_type_and_original_text_equal_by_type": dict(matched),
        "native_id_type_equal_by_type": dict(native_equal),
        "subagent_activity_original_metadata_equal": subagent_metadata_equal,
        "source_items_not_yet_projected_by_type": dict(missing), "unequal_counts": dict(unequal),
        "excluded_without_visible_text": dict(excluded),
        "source_types_outside_supported_adapter_profile": dict(unsupported),
        "projected_item_count": len(actual), "duplicate_native_key_count": duplicates,
        "source_bytes_read_selected_family": bytes_read,
        "native_receipt_count": len(native_cursors),
        "native_receipts_not_hydrating": sum(not c.get("hydrating") for c in native_cursors),
        "native_receipt_revisions": sorted(c["revision"] for c in native_cursors if isinstance(c.get("revision"), int)),
        "rollout_normalization_versions": sorted({str(c.get("normalization_version")) for c in cursor_rows if "offset" in c}),
        "source_health_states": [{"state": h.get("state"), "detail": h.get("detail")} for h in source_health],
        "cli_versions": sorted({m.get("cli_version", "unknown") for m, _ in family.values()}),
        "installed_vscode_codex_extension_versions": sorted(set(extension_versions)),
        "os": platform.system(), "kernel": platform.release(),
        "family_ipc_activity_states": dict(activity),
        "latest_native_turn_lifecycle_equal_states": dict(lifecycle_equal),
        "latest_native_turn_lifecycle_unequal_states": dict(lifecycle_unequal),
        "family_activity_provenance": dict(provenance),
        "rollout_cursor_native_identity_equal": cursor_native_equal,
        "rollout_cursor_native_identity_unequal": cursor_native_unequal,
        "family_relationship_evidence": "selected-session metadata; runtime activity only where separate IPC activity records exist",
        "latency": {"status": "NOT_MEASURED", "samples": 0, "reason": "No provider-receive and projection-receive monotonic timestamp pair captured."},
        "private_text_exported": False, "source_mutated": False,
        "limitations": ["Concurrent source/collector activity may leave a tail pending; equality assertions cover completed native items only.", "This comparison does not itself prove simultaneous live child lifecycle or browser behavior."],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--project", default="waypoint")
    parser.add_argument("--rollouts", type=Path, required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ipc-snapshot", type=Path, help="Optional bounded read-only hydration of the existing selected owner")
    args = parser.parse_args()
    family = selected_family(args.rollouts, args.root)
    if args.root not in family:
        parser.error("Selected root metadata not found")
    report = compare(args.database, args.project, family)
    if args.ipc_snapshot:
        state, observation = ipc_snapshot(args.ipc_snapshot, args.root)
        report["actual_owner_ipc"] = {**observation, **compare_ipc(state, args.database, args.project, args.root)}
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
