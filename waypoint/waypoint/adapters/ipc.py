"""Private VS Code follower client, derived from the owner's P09 observed protocol.

Only observation RPCs exist here. A caller cannot supply an arbitrary RPC method.
No Codex process is started. Connection and following subscriptions are cleaned up.
"""
from __future__ import annotations
import select
import socket
import time
import uuid
import os
import stat
import struct
from collections import deque
from pathlib import Path
from typing import Callable
from ..domain import ContractError
from .patches import FrameDecoder, RevisionState, encode_frame

ALLOWED_REQUESTS = frozenset({"initialize", "thread-owner-discovery", "thread-follower-load-complete-history"})
FOLLOW_METHOD = "thread-stream-following-changed"


class Follower:
    def __init__(self, path: Path, on_state: Callable[[str, dict, bool], None], on_health: Callable[[str, str], None], max_frame: int = 32 * 1024 * 1024, on_change: Callable | None = None):
        self.path, self.on_state, self.on_health = path, on_state, on_health
        self.on_change = on_change
        self.sock: socket.socket | None = None
        self.decoder = FrameDecoder(max_frame)
        self.client = "waypoint-initializing-" + uuid.uuid4().hex[:12]
        self.responses: dict[str, dict] = {}
        self.states: dict[str, RevisionState] = {}
        self.owners: dict[str, str] = {}
        self.needs_snapshot: set[str] = set()
        self.next_resync: dict[str, float] = {}
        self.sequence = 0
        self.sent_methods = deque(maxlen=256)

    def connect(self):
        info = self.path.stat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
            raise ContractError("ipc_owner", "IPC path must be a socket owned by the current user")
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(3)
        self.sock.connect(str(self.path))
        if hasattr(socket, "SO_PEERCRED"):
            _, uid, _ = struct.unpack("3i", self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid != os.getuid():
                self.close()
                raise ContractError("ipc_owner", "IPC peer is not the current OS user")
        self.sock.setblocking(False)
        reply = self._rpc("initialize", {"clientType": "waypoint-readonly-observer"})
        self.client = reply["result"]["clientId"]
        if not isinstance(self.client, str):
            raise ContractError("ipc_initialize", "IPC returned no client identity")
        self.on_health("connected", "Private observation IPC; no execution RPCs")

    def _send(self, message: dict):
        if self.sock is None:
            raise ConnectionError("No IPC connection")
        kind = message.get("type")
        if kind == "request" and message.get("method") not in ALLOWED_REQUESTS:
            raise ContractError("rpc_forbidden", "Execution/control RPCs are not supported")
        if kind == "broadcast" and message.get("method") != FOLLOW_METHOD:
            raise ContractError("rpc_forbidden", "Only follow/unfollow broadcast is allowed")
        if kind == "client-discovery-response" and message.get("response") != {"canHandle": False}:
            raise ContractError("rpc_forbidden", "Observer must never claim it can execute requests")
        if kind not in {"request", "broadcast", "client-discovery-response"}:
            raise ContractError("rpc_forbidden", "Unknown outgoing message type")
        self.sent_methods.append(message.get("method", kind))
        self.sock.settimeout(3)
        try:
            self.sock.sendall(encode_frame(message))
        finally:
            self.sock.setblocking(False)

    def _rpc(self, method: str, params: dict, version: int = 0, target: str | None = None) -> dict:
        if method not in ALLOWED_REQUESTS:
            raise ContractError("rpc_forbidden", "Only observed read operations are available")
        self.sequence += 1
        request_id = f"wp-{self.sequence}-{uuid.uuid4().hex[:8]}"
        msg = {"type": "request", "requestId": request_id, "sourceClientId": self.client, "version": version, "method": method, "params": params, "timeoutMs": 3000}
        if target:
            msg["targetClientId"] = target
        self._send(msg)
        deadline = time.monotonic() + 4
        while request_id not in self.responses:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"IPC {method} timed out")
            self.pump(0.05)
        reply = self.responses.pop(request_id)
        if reply.get("resultType") != "success":
            # Do not put raw provider error bodies in diagnostics/exports.
            raise ContractError("ipc_reply", f"Read-only IPC operation {method} was not successful", {"result_type": reply.get("resultType")})
        return reply

    def follow(self, thread: str):
        if thread in self.owners:
            return
        reply = self._rpc("thread-owner-discovery", {"hostId": "local", "conversationId": thread}, 1)
        owner = reply.get("handledByClientId")
        if not isinstance(owner, str):
            raise ContractError("owner_missing", "No live owner was identified")
        self.owners[thread] = owner
        self.states[thread] = RevisionState()
        self._follow_message(thread, True)
        self._rpc("thread-follower-load-complete-history", {"conversationId": thread}, 1, owner)

    def _follow_message(self, thread: str, following: bool):
        self._send({"type": "broadcast", "method": FOLLOW_METHOD, "sourceClientId": self.client, "targetClientIds": [self.owners[thread]], "version": 1, "params": {"hostId": "local", "conversationId": thread, "following": following}})

    def pump(self, timeout: float = 0.1):
        if self.sock is None:
            raise ConnectionError("No connection")
        if not select.select([self.sock], [], [], timeout)[0]:
            return
        chunk = self.sock.recv(65536)
        if not chunk:
            raise ConnectionError("IPC source disconnected")
        for msg in self.decoder.feed(chunk):
            if msg.get("type") == "response":
                if len(self.responses) > 256:
                    raise ContractError("reply_buffer", "Unexpected pending reply overflow")
                self.responses[msg.get("requestId")] = msg
            elif msg.get("type") == "client-discovery-request":
                self._send({"type": "client-discovery-response", "requestId": msg["requestId"], "response": {"canHandle": False}})
            elif msg.get("type") == "broadcast" and msg.get("method") == "thread-stream-state-changed":
                params = msg.get("params", {})
                if not isinstance(params, dict):
                    raise ContractError("ipc_params", "State event parameters must be an object")
                thread = params.get("conversationId")
                if thread not in self.states or params.get("hostId", "local") != "local":
                    continue
                state = self.states[thread]
                change = params.get("change", {})
                try:
                    accepted = state.accept(change)
                except ContractError as exc:
                    self.on_health("gap", exc.code)
                    self.needs_snapshot.add(thread)
                    continue
                if accepted:
                    # Sink failures escape frame dispatch. Received state is never
                    # mistaken for a durable acknowledgement by the collector.
                    historical = change.get("type") == "snapshot"
                    if self.on_change is not None:
                        self.on_change(thread, state.state, historical, change)
                    else:
                        self.on_state(thread, state.state, historical)
                    self.needs_snapshot.discard(thread)

    def resync(self):
        """Call outside pump/_rpc to avoid reentrant RPC during frame dispatch."""
        for thread in list(self.needs_snapshot):
            if time.monotonic() < self.next_resync.get(thread, 0):
                continue
            self.next_resync[thread] = time.monotonic() + 5
            self._rpc("thread-follower-load-complete-history", {"conversationId": thread}, 1, self.owners[thread])

    def close(self):
        if self.sock is not None:
            for thread in list(self.owners):
                try:
                    self._follow_message(thread, False)
                except (OSError, ContractError):
                    pass
            self.sock.close()
        self.sock = None
        self.owners.clear()
        self.responses.clear()
        self.states.clear()
