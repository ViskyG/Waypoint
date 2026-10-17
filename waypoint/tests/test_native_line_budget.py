"""Regression for the observed 3,147,537-byte native Codex rollout record.

Content is synthetic; the size comes from the N08 read-only native inspection.
The cap remains finite and failed reads must never consume source locations.
"""
import json

import pytest

from waypoint.adapters.codex import JsonlTail
from waypoint.collector import Collector
from waypoint.domain import ContractError


def test_complete_native_sized_line_and_restart_cursor(tmp_path):
    source = tmp_path / "large.jsonl"
    encoded = json.dumps({"type": "response_item", "payload": {"text": ""}}).encode()
    size = 3_147_537
    record = json.dumps({"type": "response_item", "payload": {"text": "x" * (size - len(encoded) - 1)}}).encode() + b"\n"
    assert len(record) == size
    source.write_bytes(record + b'{"type":"after"}\n')

    reader = JsonlTail(source)
    rows, cursor = reader.read(limit=1)
    assert len(rows) == 1 and rows[0][1]["type"] == "response_item"
    assert cursor["offset"] == size
    resumed = JsonlTail(source, cursor)
    following, after = resumed.read(limit=1)
    assert [row[1]["type"] for row in following] == ["after"]
    assert after["offset"] == source.stat().st_size
    assert JsonlTail(source, after).read()[0] == []


def test_oversized_line_keeps_entire_uncommitted_cursor(tmp_path):
    source = tmp_path / "bounded.jsonl"
    source.write_bytes(b'{"type":"before"}\n' + b"x" * (16 * 1024 * 1024 + 1) + b"\n")
    reader = JsonlTail(source)
    with pytest.raises(ContractError) as error:
        reader.read()
    assert error.value.code == "rollout_line_size"
    assert reader.offset == 0 and reader.generation is None


def test_rollout_recovery_health_requires_committed_round_and_does_not_repeat(tmp_path):
    class Sink:
        def __init__(self):
            self.cursor = None
            self.events = []

        def call(self, method, path, body=None):
            if method == "GET":
                return self.cursor
            self.events.extend(body["events"])
            if "cursor" in body:
                self.cursor = body["cursor"]

    source = tmp_path / "selected.jsonl"
    source.write_text(json.dumps({"type": "session_meta", "payload": {"id": "root"}}) + "\n")
    sink = Sink()
    collector = Collector(sink, "p", "root", tmp_path / "unused.sock", tmp_path)
    collector.family = {"root": ({"id": "root"}, source)}
    collector.tail_once()
    first_cursor = dict(sink.cursor)

    def health():
        return [event for event in sink.events if event["kind"] == "source.health"]

    assert [event["payload"]["state"] for event in health()] == ["connected"]
    assert health()[0]["source"] == collector.rollout_source
    collector.tail_once()
    assert len(health()) == 1 and sink.cursor == first_cursor

    # A failed round may not emit a successful recovery receipt or consume bytes.
    with source.open("a") as stream:
        stream.write("not-json\n")
    with pytest.raises(ContractError):
        collector.tail_once()
    assert len(health()) == 1 and sink.cursor == first_cursor
    collector.health("gap", "rollout_json", collector.rollout_source)
    source.write_text(json.dumps({"type": "session_meta", "payload": {"id": "root"}}) + "\n")
    collector.tail_once()
    collector.tail_once()
    assert [event["payload"]["state"] for event in health()] == ["connected", "gap", "connected"]
    assert sink.cursor == first_cursor
