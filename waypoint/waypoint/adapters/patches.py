"""Observed VS Code IPC frame format and atomic path-array patches.

This is NOT an official OpenAI contract and not RFC 6902's JSON Pointer format.
Profile basis: owner's successful P09 probe, extension 26.930.61225 on Linux.
"""
from __future__ import annotations
import copy
import json
import struct
from collections import OrderedDict
from typing import Any
from ..domain import ContractError, digest


class FrameDecoder:
    def __init__(self, max_frame: int = 32 * 1024 * 1024):
        self.buffer = bytearray()
        self.max_frame = max_frame

    def feed(self, data: bytes) -> list[dict]:
        self.buffer.extend(data)
        messages = []
        while len(self.buffer) >= 4:
            length = struct.unpack_from("<I", self.buffer)[0]
            if not 0 < length <= self.max_frame:
                self.buffer.clear()
                raise ContractError("frame_size", "IPC frame exceeds configured bound or is invalid")
            if len(self.buffer) < length + 4:
                break
            raw = bytes(self.buffer[4:length + 4])
            del self.buffer[:length + 4]
            try:
                message = json.loads(raw)
            except (ValueError, UnicodeDecodeError, RecursionError) as exc:
                raise ContractError("frame_json", "Invalid IPC JSON frame") from exc
            if not isinstance(message, dict):
                raise ContractError("frame_shape", "IPC envelope must be an object")
            messages.append(message)
        # Callers read bounded chunks; this checks stalled/malformed partial data.
        if len(self.buffer) > self.max_frame + 4:
            self.buffer.clear()
            raise ContractError("frame_buffer", "IPC buffered data exceeds cap")
        return messages


def encode_frame(value: dict) -> bytes:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    return struct.pack("<I", len(raw)) + raw


def _index(key: Any, length: int, allow_end: bool = False) -> int:
    if isinstance(key, bool) or not isinstance(key, int):
        raise ContractError("patch_path", "List patch path requires an integer")
    if key < 0 or key >= length + (1 if allow_end else 0):
        raise ContractError("patch_path", "List patch index outside bounds")
    return key


def _operation(value: Any, path: list, op: str, replacement: Any) -> Any:
    if not path:
        if op == "remove":
            raise ContractError("patch_root", "Removing the whole conversation is not a valid state patch")
        return copy.deepcopy(replacement)
    key, tail = path[0], path[1:]
    if isinstance(value, dict):
        if not isinstance(key, str):
            raise ContractError("patch_path", "Object patch path requires a string")
        candidate = value.copy()
        if tail:
            if key not in value:
                raise ContractError("patch_path", "Unknown parent patch path")
            candidate[key] = _operation(value[key], tail, op, replacement)
        elif op == "remove":
            if key not in value:
                raise ContractError("patch_path", "Cannot remove absent member")
            del candidate[key]
        else:
            if op == "replace" and key not in value:
                raise ContractError("patch_path", "Cannot replace absent member")
            candidate[key] = copy.deepcopy(replacement)
        return candidate
    if isinstance(value, list):
        index = _index(key, len(value), op == "add" and not tail)
        candidate = value.copy()
        if tail:
            candidate[index] = _operation(value[index], tail, op, replacement)
        elif op == "remove":
            candidate.pop(index)
        elif op == "add":
            candidate.insert(index, copy.deepcopy(replacement))
        else:
            candidate[index] = copy.deepcopy(replacement)
        return candidate
    raise ContractError("patch_path", "Patch attempts to traverse a scalar")


def apply_patches(state: dict, patches: list[dict]) -> dict:
    if not isinstance(patches, list) or len(patches) > 100_000:
        raise ContractError("patch_size", "Invalid patch batch")
    candidate: Any = state
    for patch in patches:
        if not isinstance(patch, dict):
            raise ContractError("patch_shape", "Patch entry must be an object")
        op, path = patch.get("op"), patch.get("path")
        if op not in {"add", "remove", "replace"} or not isinstance(path, list) or len(path) > 128:
            raise ContractError("patch_operation", "Unsupported private patch operation/path")
        if op != "remove" and "value" not in patch:
            raise ContractError("patch_value", "Patch value missing")
        candidate = _operation(candidate, path, op, patch.get("value"))
    if not isinstance(candidate, dict):
        raise ContractError("patch_root", "Conversation state must remain an object")
    return candidate


class RevisionState:
    """Received source state; a consumer's durable cursor is a separate boundary."""
    def __init__(self, recent_limit: int = 256):
        self.state: dict | None = None
        self.revision: int | None = None
        self.valid = False
        self.recent_limit = max(1, recent_limit)
        self.recent: OrderedDict[int, str] = OrderedDict()

    def accept(self, change: dict) -> bool:
        if not isinstance(change, dict):
            self.valid = False
            raise ContractError("change_shape", "Source change must be an object")
        rev = change.get("revision")
        if isinstance(rev, bool) or not isinstance(rev, int) or rev < 0:
            self.valid = False
            raise ContractError("revision", "Invalid source revision")
        kind = change.get("type")
        if kind not in {"snapshot", "patches"}:
            self.valid = False
            raise ContractError("change_type", "Unknown source change type")
        fingerprint = digest(change)
        cached = self.recent.get(rev)
        if cached is not None:
            if cached == fingerprint and self.valid:
                return False
            # A requested authoritative snapshot repairs an invalid stream.
            if not (kind == "snapshot" and not self.valid):
                self.valid = False
                raise ContractError("revision_conflict", "Different source change at a cached revision; snapshot required")
        elif self.valid and self.revision is not None and rev <= self.revision:
            return False  # outside cache: stale, no byte-consistency claim
        if kind == "snapshot":
            candidate = change.get("conversationState")
            if not isinstance(candidate, dict):
                self.valid = False
                raise ContractError("snapshot", "Missing conversationState")
            try:
                candidate = copy.deepcopy(candidate)
            except RecursionError as exc:
                self.valid = False
                raise ContractError("state_depth", "Conversation nesting exceeds parser budget") from exc
            if not self.valid:
                self.recent.clear()
        else:
            if not self.valid or self.state is None or change.get("baseRevision") != self.revision or rev <= self.revision:
                self.valid = False
                raise ContractError("revision_gap", "Snapshot required before more patches")
            try:
                candidate = apply_patches(self.state, change.get("patches"))
            except ContractError:
                self.valid = False
                raise
        self.state, self.revision, self.valid = candidate, rev, True
        self.recent[rev] = fingerprint
        while len(self.recent) > self.recent_limit:
            self.recent.popitem(last=False)
        return True
