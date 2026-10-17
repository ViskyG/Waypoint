"""Synthetic contracts. These tests do not establish a live Codex connection."""
from __future__ import annotations
import copy
from urllib.parse import parse_qs, urlsplit
import pytest
from waypoint.adapters.codex import Normalizer, bounded_content
from waypoint.adapters.patches import RevisionState, apply_patches
from waypoint.collector import Collector
from waypoint.domain import ContractError, canonical
from waypoint.client import Unavailable
from waypoint.store import Store


def state_with_items(count=1):
    return {"id": "r", "threadRuntimeStatus": {"type": "active"}, "turns": [{"items": [{"id": f"m{i}", "type": "agentMessage", "text": "original", "status": "running"} for i in range(count)]}]}


def test_dirty_item_does_not_walk_other_history_and_preserves_first_revision():
    normalizer = Normalizer("p", "ipc", "g")
    state = state_with_items(1000)
    normalizer.snapshot(state, "r", True, {"type": "snapshot", "revision": 8}, "ipc:p:r")
    patches = [{"op": "replace", "path": ["turns", 0, "items", 501, "text"], "value": "new exact text"}]
    changed = apply_patches(state, patches)
    events = normalizer.snapshot(changed, "r", False, {"type": "patches", "revision": 9, "patches": patches}, "ipc:p:r")
    items = [e["payload"] for e in events if e["kind"] == "item.upsert"]
    assert len(items) == 1 and items[0]["item_id"] == "m501"
    assert items[0]["source_first_revision"] == 8 and items[0]["source_revision"] == 9
    assert normalizer.last_work == {"visited": 0, "normalized": 1, "rebuilds": 0}


def test_array_shift_reindexes_only_changed_container_and_new_item_boundary():
    normalizer = Normalizer("p", "ipc", "g")
    state = state_with_items(2)
    state["turns"].append({"items": [{"id": "other", "type": "userMessage", "text": "untouched"}]})
    normalizer.snapshot(state, "r", True, {"type": "snapshot", "revision": 2})
    patches = [{"op": "add", "path": ["turns", 0, "items", 0], "value": {"id": "fresh", "type": "agentMessage", "text": "fresh"}}]
    changed = apply_patches(state, patches)
    events = normalizer.snapshot(changed, "r", False, {"type": "patches", "revision": 3, "patches": patches})
    items = [e["payload"] for e in events if e["kind"] == "item.upsert"]
    assert [i["item_id"] for i in items] == ["fresh"]
    assert items[0]["source_first_revision"] == 3
    assert normalizer.last_work == {"visited": 4, "normalized": 3, "rebuilds": 1}
    patch = [{"op": "replace", "path": ["turns", 0, "items", 2, "text"], "value": "shifted"}]
    events = normalizer.snapshot(apply_patches(changed, patch), "r", False, {"type": "patches", "revision": 4, "patches": patch})
    assert [e["payload"]["item_id"] for e in events if e["kind"] == "item.upsert"] == ["m1"]


def test_unknown_history_structure_rebuild_is_diagnosed_and_settings_excluded():
    normalizer = Normalizer("p", "ipc", "g")
    state = state_with_items()
    state["turns"][0]["unknown"] = 1
    normalizer.snapshot(state, "r", True)
    patch = [{"op": "replace", "path": ["turns", 0, "unknown"], "value": {"id": "found", "type": "agentMessage", "text": "visible"}}]
    events = normalizer.snapshot(apply_patches(state, patch), "r", False, {"type": "patches", "revision": 2, "patches": patch})
    assert any(e["kind"] == "source.health" and e["payload"]["detail"] == "unknown_history_structure" for e in events)
    assert any(e["payload"].get("item_id") == "found" for e in events)
    state = apply_patches(state, patch)
    patch = [{"op": "add", "path": ["latestThreadSettings"], "value": {"id": "private", "type": "agentMessage", "text": "never collected"}}]
    normalizer.snapshot(apply_patches(state, patch), "r", False, {"type": "patches", "revision": 3, "patches": patch})
    assert normalizer.last_work["visited"] == normalizer.last_work["normalized"] == 0


def test_recent_duplicate_conflict_gap_and_bounded_stale_cache():
    revision = RevisionState(recent_limit=2)
    first = {"type": "snapshot", "revision": 1, "conversationState": {"n": 0}}
    assert revision.accept(first) and not revision.accept(copy.deepcopy(first))
    second = {"type": "patches", "baseRevision": 1, "revision": 2, "patches": [{"op": "replace", "path": ["n"], "value": 1}]}
    assert revision.accept(second) and not revision.accept(second)
    conflict = copy.deepcopy(second)
    conflict["patches"][0]["value"] = 2
    with pytest.raises(ContractError, match="cached revision") as exc:
        revision.accept(conflict)
    assert exc.value.code == "revision_conflict" and revision.state["n"] == 1 and not revision.valid
    assert revision.accept({"type": "snapshot", "revision": 2, "conversationState": {"n": 1}})
    with pytest.raises(ContractError) as exc:
        revision.accept({"type": "patches", "baseRevision": 1, "revision": 3, "patches": []})
    assert exc.value.code == "revision_gap"
    revision.accept({"type": "snapshot", "revision": 10, "conversationState": {"n": 1}})
    for rev in range(11, 15):
        revision.accept({"type": "patches", "baseRevision": rev - 1, "revision": rev, "patches": []})
    assert len(revision.recent) == 2 and not revision.accept(first)


class StoreSink:
    def __init__(self, tmp_path, fail_after=None):
        self.directory = tmp_path
        self.store = Store(tmp_path / "test.sqlite3")
        self.posts = []
        self.fail_after = fail_after
    def call(self, method, path, body=None):
        if method == "GET":
            key = parse_qs(urlsplit(path).query)["source_key"][0]
            return self.store.cursor(key) or {}
        self.posts.append(copy.deepcopy(body))
        result = self.store.ingest(body["events"], body.get("cursor"), "p")
        if self.fail_after == len(self.posts):
            raise Unavailable("synthetic lost durable receipt")
        return result


def test_snapshot_barrier_and_lost_receipt_replay_use_real_sqlite(tmp_path):
    sink = StoreSink(tmp_path, fail_after=2)
    collector = Collector(sink, "p", "r", tmp_path / "ipc", tmp_path, coalesce_seconds=0.2)
    state = state_with_items(405)
    with pytest.raises(Unavailable):
        collector.snapshot("r", state, True, {"type": "snapshot", "revision": 10})
    cursor = sink.store.cursor("ipc:p:r")
    assert cursor["hydrating"] is True and cursor["revision"] is None and cursor["received_revision"] == 10
    assert collector.committed["r"] == {}
    committed_count = sink.store.db.execute("SELECT count(*) FROM events").fetchone()[0]
    collector.flush(force=True)
    assert sink.posts[1] == sink.posts[2]  # exact body replay, including timestamps
    assert collector.committed["r"]["revision"] == 10
    assert sink.store.cursor("ipc:p:r")["hydrating"] is False
    count = sink.store.db.execute("SELECT count(*) FROM items").fetchone()[0]
    assert count == 405
    assert sink.store.db.execute("SELECT count(*) FROM events").fetchone()[0] == 409
    assert committed_count == 400


def test_text_coalesces_terminal_flush_is_immediate_and_exact(tmp_path):
    sink = StoreSink(tmp_path)
    collector = Collector(sink, "p", "r", tmp_path / "ipc", tmp_path, coalesce_seconds=0.2)
    state = state_with_items()
    collector.snapshot("r", state, True, {"type": "snapshot", "revision": 1})
    baseline = len(sink.posts)
    for revision, text in [(2, "part"), (3, "part exact")]:
        patch = [{"op": "replace", "path": ["turns", 0, "items", 0, "text"], "value": text}]
        state = apply_patches(state, patch)
        collector.snapshot("r", state, False, {"type": "patches", "revision": revision, "patches": patch})
    assert len(sink.posts) == baseline
    assert collector.committed["r"]["revision"] == 1
    collector.flush()
    assert len(sink.posts) == baseline
    patch = [{"op": "replace", "path": ["turns", 0, "items", 0, "status"], "value": "completed"}]
    state = apply_patches(state, patch)
    collector.snapshot("r", state, False, {"type": "patches", "revision": 4, "patches": patch})
    assert len(sink.posts) == baseline + 1 and collector.committed["r"]["revision"] == 4
    emitted = [e["payload"] for e in sink.posts[-1]["events"] if e["kind"] == "item.upsert"]
    assert len(emitted) == 1 and emitted[0]["text"] == "part exact" and emitted[0]["state"] == "completed"


def test_visible_native_reasoning_summary_and_serialized_byte_cap():
    normalizer = Normalizer("p", "file", "g")
    native, events = normalizer.rollout({"type": "event_msg", "payload": {"type": "item_completed", "item": {"id": "r1", "type": "Reasoning", "summary_text": "visible summary"}}}, "r", "record")
    assert events[0]["payload"]["text"] == "visible summary" and events[0]["payload"]["content_origin"] == "provider_summary"
    text, truncated = bounded_content("\x00🙂" * 400_000)
    assert truncated and len(canonical(text).encode()) <= 1_900_000


def test_whole_state_patch_rebuilds_both_roots_and_item_identity_change():
    normalizer = Normalizer("p", "ipc", "g")
    state = state_with_items()
    normalizer.snapshot(state, "r", True, {"type": "snapshot", "revision": 1})
    new_state = state_with_items()
    new_state["turnHistory"] = {"history": {"entitiesByKey": {"extra": {"id": "second-root", "type": "userMessage", "text": "exact"}}}}
    patch = [{"op": "replace", "path": [], "value": new_state}]
    events = normalizer.snapshot(new_state, "r", False, {"type": "patches", "revision": 2, "patches": patch})
    assert any(e["payload"].get("item_id") == "second-root" for e in events)
    patch = [{"op": "replace", "path": ["turns", 0, "items", 0, "id"], "value": "renamed-native"}]
    new_state = apply_patches(new_state, patch)
    events = normalizer.snapshot(new_state, "r", False, {"type": "patches", "revision": 3, "patches": patch})
    assert next(e["payload"] for e in events if e["kind"] == "item.upsert")["source_first_revision"] == 3
    patch = [{"op": "replace", "path": ["turns", 0, "items", 0, "text"], "value": "later"}]
    events = normalizer.snapshot(apply_patches(new_state, patch), "r", False, {"type": "patches", "revision": 4, "patches": patch})
    assert next(e["payload"] for e in events if e["kind"] == "item.upsert")["source_first_revision"] == 3


def test_observed_nested_thread_spawn_keeps_distinct_identity_and_genealogy():
    normalizer = Normalizer("p", "file", "g")
    meta = {"id": "child", "session_id": "shared", "source": {"subagent": {"thread_spawn": {"parent_thread_id": "root", "agent_path": "/root/child", "agent_nickname": "worker", "depth": 1}}}}
    event = normalizer.metadata(meta)
    assert event["agent_id"] == "codex/child"
    assert event["payload"]["parent_id"] == "codex/root" and event["payload"]["agent_path"] == "/root/child"
    assert event["payload"]["session_id"] == "shared" and event["payload"]["name"] == "worker"


def test_serialized_batches_respect_http_bound():
    from waypoint.collector import event_batches
    events = [{"text": "x" * 1_900_000, "n": i} for i in range(8)]
    batches = list(event_batches(events))
    assert list(map(len, batches)) == [3, 3, 2]
    assert all(len(canonical({"events": b}).encode()) < 8_000_000 for b in batches)


def test_native_lifecycle_reports_own_turn_and_keeps_history_provenance():
    normalizer = Normalizer("p", "file", "g")
    for source_kind, expected in [("task_started", "running"), ("task_complete", "idle")]:
        native, events = normalizer.rollout({"timestamp": "2026-10-17T10:00:00Z", "type": "event_msg", "payload": {"type": source_kind, "turn_id": "turn-1", "last_agent_message": "must not collect"}}, "child", source_kind, True)
        assert len(events) == 1 and events[0]["kind"] == "agent.activity"
        assert events[0]["agent_id"] == "codex/child"
        assert events[0]["payload"] == {"state": expected, "reported_by": "event_msg." + source_kind, "turn_id": "turn-1", "historical": True}
        assert "must not collect" not in canonical(events)


def test_native_subagent_operation_preserves_fields_without_invented_text_or_activity():
    normalizer = Normalizer("p", "file", "g")
    item = {"type": "SubAgentActivity", "id": "op", "kind": "completed", "agent_thread_id": "child", "agent_path": "/root/child"}
    _, events = normalizer.rollout({"type": "event_msg", "payload": {"type": "item_completed", "item": item, "thread_id": "root", "turn_id": "turn-1"}}, "root", "record")
    assert len(events) == 1 and events[0]["kind"] == "item.upsert" and events[0]["agent_id"] == "codex/root"
    payload = events[0]["payload"]
    assert payload["text"] == "" and payload["type"] == "subAgentActivity"
    assert payload["kind"] == "completed" and payload["agent_thread_id"] == "child" and payload["agent_path"] == "/root/child"


def test_rollout_mapping_upgrade_replays_selected_source_without_changing_record_identity(tmp_path):
    import json
    from waypoint.adapters.codex import JsonlTail
    from waypoint.domain import digest
    source = tmp_path / "rollout.jsonl"
    rows = [
        {"timestamp": "2026-10-17T08:00:00Z", "type": "session_meta", "payload": {"id": "r"}},
        {"timestamp": "2026-10-17T08:00:01Z", "type": "event_msg", "payload": {"type": "task_complete", "turn_id": "t"}},
    ]
    source.write_text("".join(json.dumps(row) + "\n" for row in rows))
    sink = StoreSink(tmp_path)
    old_reader = JsonlTail(source)
    old_rows, cursor = old_reader.read()
    key = "rollout:p:" + digest(str(source.resolve()))[:32]
    cursor.update(source_key=key, native_id="r")
    normalizer = Normalizer("p", "codex-rollout/" + digest("r")[:12], old_reader.generation)
    metadata = normalizer.rollout(old_rows[0][1], None, old_rows[0][0])[1]
    sink.store.ingest(metadata, cursor, "p")
    collector = Collector(sink, "p", "r", tmp_path / "ipc", tmp_path)
    collector.family = {"r": ({"id": "r"}, source)}
    collector.tail_once()
    assert sink.store.db.execute("SELECT count(*) FROM events WHERE kind='agent.upsert'").fetchone()[0] == 1
    assert sink.store.db.execute("SELECT count(*) FROM events WHERE kind='agent.activity'").fetchone()[0] == 1
    saved = sink.store.cursor(key)
    assert saved["normalization_version"] == 3 and saved["offset"] == source.stat().st_size
    assert saved["generation"] == cursor["generation"] and saved["file_identity"] == cursor["file_identity"]
    collector.tail_once()
    assert sink.store.db.execute("SELECT count(*) FROM events").fetchone()[0] == 2


def test_recreated_ipc_observer_fresh_timestamp_does_not_reuse_receipt_identity(tmp_path, monkeypatch):
    import waypoint.adapters.codex as codex
    sink = StoreSink(tmp_path)
    state = state_with_items()
    monkeypatch.setattr(codex, "now", lambda: "2026-10-17T10:00:00Z")
    first = Normalizer("p", "ipc", "persisted-generation").snapshot(state, "r", True, {"type": "snapshot", "revision": 10})
    sink.store.ingest(first, project="p")
    monkeypatch.setattr(codex, "now", lambda: "2026-10-17T10:01:00Z")
    restarted = Normalizer("p", "ipc", "persisted-generation").snapshot(state, "r", True, {"type": "snapshot", "revision": 10})
    assert {event["event_id"] for event in first}.isdisjoint({event["event_id"] for event in restarted})
    sink.store.ingest(restarted, project="p")
    assert sink.store.db.execute("SELECT count(*) FROM items").fetchone()[0] == 1
    assert all(not receipt["created"] for receipt in sink.store.ingest(restarted, project="p")["receipts"])
    row = {"timestamp": "2026-10-17T09:00:00Z", "type": "session_meta", "payload": {"id": "r"}}
    old = Normalizer("p", "file", "persisted-generation").rollout(row, None, "stable-record")[1]
    monkeypatch.setattr(codex, "now", lambda: "2026-10-17T10:02:00Z")
    replay = Normalizer("p", "file", "persisted-generation").rollout(row, None, "stable-record")[1]
    assert old == replay


def test_snapshot_missing_native_runtime_status_does_not_erase_known_activity(tmp_path):
    normalizer = Normalizer("p", "ipc", "g")
    sink = StoreSink(tmp_path)
    _, lifecycle = normalizer.rollout({"timestamp": "2026-10-17T08:00:00Z", "type": "event_msg", "payload": {"type": "task_complete", "turn_id": "t"}}, "r", "record")
    sink.store.ingest(lifecycle, project="p")
    snapshot = normalizer.snapshot({"id": "r", "turns": []}, "r", True)
    assert not any(event["kind"] == "agent.activity" for event in snapshot)
    sink.store.ingest(snapshot, project="p")
    import json
    agent = json.loads(sink.store.db.execute("SELECT body FROM agents WHERE project='p' AND id='codex/r'").fetchone()[0])
    assert agent["activity"] == "idle"


def test_fork_explicit_native_marker_restores_child_without_changing_source_location(tmp_path):
    import json
    from waypoint.adapters.codex import JsonlTail
    from waypoint.domain import digest
    source = tmp_path / "fork.jsonl"
    rows = [
        {"type": "session_meta", "payload": {"id": "child", "forked_from_id": "parent"}},
        {"type": "session_meta", "payload": {"id": "parent"}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": "copied parent"}},
        {"type": "event_msg", "payload": {"type": "thread_settings_applied", "thread_id": "child", "thread_settings": {"must_not_collect": "secret"}}},
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "child-turn"}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": "own child"}},
    ]
    source.write_text("".join(json.dumps(row) + "\n" for row in rows))
    original_reader = JsonlTail(source)
    original_rows, original_cursor = original_reader.read()
    previous = Normalizer("p", "codex-rollout/" + digest("parent")[:12], original_reader.generation)
    old_native, old_events = "child", []
    for key, row in original_rows:
        old_native, emitted = previous.rollout(row, old_native, key)
        old_events.extend(emitted)
    original_child_location = next(e["payload"]["item_id"] for e in old_events if e["payload"].get("text") == "own child")
    sink = StoreSink(tmp_path)
    source_key = "rollout:p:" + digest(str(source.resolve()))[:32]
    original_cursor.update(source_key=source_key, native_id=old_native, normalization_version=2)
    sink.store.ingest(old_events, original_cursor, "p")
    collector = Collector(sink, "p", "parent", tmp_path / "ipc", tmp_path)
    collector.family = {"child": ({"id": "child", "forked_from_id": "parent"}, source), "parent": ({"id": "parent"}, tmp_path / "missing")}
    # The selected parent is included as identity evidence but its own file is
    # not involved in this bounded source test.
    del collector.family["parent"]
    collector.family["parent"] = ({"id": "parent"}, source)
    # Avoid reading the same file twice while retaining selected-family proof.
    class Family(dict):
        def items(self):
            return [("child", self["child"])]
    collector.family = Family(collector.family)
    collector.tail_once()
    corrected = [e for post in sink.posts for e in post["events"] if e["agent_id"] == "codex/child" and e["payload"].get("text") == "own child"]
    assert len(corrected) == 1 and corrected[0]["payload"]["item_id"] == original_child_location
    assert "secret" not in canonical(sink.posts)
    saved = sink.store.cursor(source_key)
    assert saved["native_id"] == "child" and saved["fork_context"] == {"active_native": "child", "restored": True}
    assert saved["normalization_version"] == 3
    count = sink.store.db.execute("SELECT count(*) FROM events").fetchone()[0]
    collector.tail_once()
    assert sink.store.db.execute("SELECT count(*) FROM events").fetchone()[0] == count
    assert any(e["agent_id"] == "codex/parent" and e["payload"].get("text") == "copied parent" for e in old_events)


def test_unknown_fork_identity_is_quarantined_until_exact_verified_marker(tmp_path):
    import json
    source = tmp_path / "fork.jsonl"
    source.write_text("".join(json.dumps(row) + "\n" for row in [
        {"type": "session_meta", "payload": {"id": "child", "forked_from_id": "unknown-parent"}},
        {"type": "session_meta", "payload": {"id": "unknown-parent"}},
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "copied"}},
        {"type": "event_msg", "payload": {"type": "thread_settings_applied", "thread_id": "unproven"}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": "unproven copied"}},
        {"type": "event_msg", "payload": {"type": "thread_settings_applied", "thread_id": "child"}},
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "own"}},
    ]))
    sink = StoreSink(tmp_path)
    collector = Collector(sink, "p", "child", tmp_path / "ipc", tmp_path)
    collector.family = {"child": ({"id": "child", "forked_from_id": "unknown-parent"}, source)}
    collector.tail_once()
    events = [e for post in sink.posts for e in post["events"]]
    assert {e["agent_id"] for e in events} == {"codex/child"}
    activities = [e for e in events if e["kind"] == "agent.activity"]
    assert len(activities) == 1 and activities[0]["payload"]["turn_id"] == "own"
    assert not any(e["kind"] == "item.upsert" for e in events)


def test_fork_context_survives_cursor_batch_and_collector_restart(tmp_path):
    import json
    from waypoint.domain import digest
    source = tmp_path / "fork.jsonl"
    parent_file = tmp_path / "parent.jsonl"
    parent_file.write_text(json.dumps({"type": "session_meta", "payload": {"id": "parent"}}) + "\n")
    rows = [{"type": "session_meta", "payload": {"id": "child", "forked_from_id": "parent"}}, {"type": "session_meta", "payload": {"id": "parent"}}]
    rows.extend({"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": "copied"}} for _ in range(148))
    rows.extend([
        {"type": "event_msg", "payload": {"type": "thread_settings_applied", "thread_id": "child"}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": "own after restart"}},
        {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": "child-own"}},
    ])
    source.write_text("".join(json.dumps(row) + "\n" for row in rows))
    sink = StoreSink(tmp_path)
    family = {"child": ({"id": "child", "forked_from_id": "parent"}, source), "parent": ({"id": "parent"}, parent_file)}
    first = Collector(sink, "p", "parent", tmp_path / "ipc", tmp_path)
    first.family = family
    first.tail_once()
    source_key = "rollout:p:" + digest(str(source.resolve()))[:32]
    before = sink.store.cursor(source_key)
    assert before["fork_context"] == {"active_native": "parent", "restored": False}
    restarted = Collector(sink, "p", "parent", tmp_path / "ipc", tmp_path)
    restarted.family = family
    restarted.tail_once()
    after = sink.store.cursor(source_key)
    assert after["fork_context"] == {"active_native": "child", "restored": True}
    assert after["generation"] == before["generation"] and after["native_id"] == "child"
    row = sink.store.db.execute("SELECT body FROM agents WHERE id='codex/child'").fetchone()
    assert json.loads(row[0])["activity"] == "idle"
    own = [e for post in sink.posts for e in post["events"] if e["payload"].get("text") == "own after restart"]
    assert len(own) == 1 and own[0]["agent_id"] == "codex/child"
