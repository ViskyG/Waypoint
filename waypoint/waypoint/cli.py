"""Local low-churn protocol. Sparse signals do not control the actual executor."""
from __future__ import annotations
import argparse
import fcntl
import json
import os
import sys
import uuid
from pathlib import Path
from urllib.parse import quote

from .client import Client, Unavailable
from .domain import ContractError, now, validate_event
from .security import load_tokens, private_directory
from .spool import queue


def parser():
    p = argparse.ArgumentParser(prog="wp", description="Waypoint: local work observability, not an agent launcher")
    p.add_argument("--data", type=Path, default=Path(os.getenv("WP_DATA", "~/.local/share/waypoint")).expanduser())
    p.add_argument("--url", default=os.getenv("WP_URL"))
    p.add_argument("--project", default=os.getenv("WP_PROJECT"))
    p.add_argument("--agent", help="Explicit distinct identity; WP_AGENT is deliberately not inherited")
    p.add_argument("--binding", type=Path, help="Project-local binding verified against this executor's native metadata")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8769); s.add_argument("--demo", action="store_true")
    sub.add_parser("url")
    sub.add_parser("projects")
    s = sub.add_parser("bind"); s.add_argument("--rollout", type=Path, required=True); s.add_argument("--output", type=Path, required=True)
    sub.add_parser("state")
    s = sub.add_parser("packet"); s.add_argument("node")
    s = sub.add_parser("focus"); s.add_argument("nodes", nargs="*"); s.add_argument("--edges", nargs="*", default=[])
    s = sub.add_parser("status"); s.add_argument("node"); s.add_argument("text"); s.add_argument("--why", default="")
    s = sub.add_parser("done"); s.add_argument("node"); s.add_argument("--result", default=""); s.add_argument("--diff", default="")
    s = sub.add_parser("test"); s.add_argument("node"); s.add_argument("test_id"); s.add_argument("outcome", choices=["passed", "failed", "skipped", "error", "not_run"]); s.add_argument("--run", required=True); s.add_argument("--basis"); s.add_argument("--current", action="store_true")
    s = sub.add_parser("note"); s.add_argument("text"); s.add_argument("--nodes", nargs="*", default=[]); s.add_argument("--edges", nargs="*", default=[])
    s = sub.add_parser("link"); s.add_argument("item"); s.add_argument("nodes", nargs="*"); s.add_argument("--edges", nargs="*", default=[])
    s = sub.add_parser("emit"); s.add_argument("file", type=Path)
    s = sub.add_parser("plan-import"); s.add_argument("file", type=Path); s.add_argument("--base"); s.add_argument("--merge", action="store_true"); s.add_argument("--request-id", default=None)
    s = sub.add_parser("plan-export"); s.add_argument("file", type=Path); s.add_argument("--version")
    s = sub.add_parser("observe"); s.add_argument("--thread", required=True); s.add_argument("--ipc", type=Path, required=True); s.add_argument("--rollouts", type=Path, required=True); s.add_argument("--duration", type=float); s.add_argument("--max-frame-mib", type=int, default=32)
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "serve":
            return serve(args)
        if args.command == "bind":
            native = os.getenv("CODEX_THREAD_ID")
            if not native:
                raise ContractError("binding_identity", "No native caller ID supplied by this executor")
            metadata = rollout_identity(args.rollout)
            if metadata["id"] != native:
                raise ContractError("binding_identity", "Selected rollout does not belong to this executor")
            binding = {"schema": "waypoint.binding/1", "native_id": native, "agent_id": "codex/" + native, "project_id": args.project, "rollout": str(args.rollout.resolve())}
            fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump(binding, f)
            print(json.dumps({"saved": str(args.output), "verified_native_id": True}))
            return 0
        if args.binding:
            binding = json.loads(args.binding.read_text())
            if not isinstance(binding, dict) or binding.get("schema") != "waypoint.binding/1" or not isinstance(binding.get("rollout"), str):
                raise ContractError("binding_metadata", "Expected a verified project-local binding")
            metadata = rollout_identity(Path(binding["rollout"]))
            native = os.getenv("CODEX_THREAD_ID")
            if not native or metadata["id"] != native or binding.get("native_id") != native or binding.get("agent_id") != "codex/" + native or binding.get("project_id") != args.project:
                raise ContractError("binding_identity", "Binding does not match this executor and project")
            if args.agent and args.agent != binding["agent_id"]:
                raise ContractError("binding_identity", "Explicit agent differs from verified binding")
            args.agent = binding["agent_id"]
        client = Client(args.data, args.url)
        if args.command == "url":
            print(client.url + "/#key=" + client.tokens["read"])
            return 0
        if args.command == "projects":
            reply = client.call("GET", "/api/projects")
        else:
            if not args.project:
                raise ContractError("project_required", "Use --project or WP_PROJECT")
            base = "/api/p/" + quote(args.project, safe="")
            if args.command == "state":
                reply = client.call("GET", base + "/state")
            elif args.command == "packet":
                reply = client.call("GET", base + "/packet/" + quote(args.node, safe=""))
            elif args.command == "plan-export":
                suffix = "?version=" + quote(args.version) if args.version else ""
                reply = client.call("GET", base + "/plan" + suffix)
                output = {"base_version": reply["version"], "plan": reply["plan"]}
                # Never overwrite an existing user file by an implicit export.
                with args.file.open("x", encoding="utf-8") as f:
                    json.dump(output, f, ensure_ascii=False, indent=2)
                reply = {"saved": str(args.file), "version": reply["version"], "runtime_content_exported": False}
            elif args.command == "plan-import":
                value = json.loads(args.file.read_text(encoding="utf-8"))
                payload = {"plan": value.get("plan", value), "base_version": args.base or value.get("base_version"), "request_id": args.request_id or value.get("request_id") or uuid.uuid4().hex, "merge": args.merge}
                reply = client.call("POST", base + "/plans", payload)
            elif args.command == "observe":
                from .collector import Collector
                Collector(client, args.project, args.thread, args.ipc, args.rollouts, max_frame=args.max_frame_mib * 1024 * 1024).run(args.duration)
                reply = {"observer": "stopped", "agent_control": False}
            else:
                events = signals(args)
                if args.command == "focus" and args.agent.startswith("codex/"):
                    from urllib.parse import urlencode
                    key = "ipc:" + args.project + ":" + args.agent.removeprefix("codex/")
                    try:
                        cursor = client.call("GET", "/api/cursor?" + urlencode({"source_key": key}))
                        if not cursor.get("hydrating") and isinstance(cursor.get("revision"), int):
                            events[0]["payload"]["source_boundary"] = {"source_key": key, "generation": cursor.get("generation"), "revision": cursor["revision"]}
                    except Unavailable:
                        pass  # queued focus has no invented native watermark
                try:
                    reply = client.call("POST", base + "/events", {"events": events})
                except Unavailable:
                    receipt = queue(args.data, events)
                    reply = {"delivery": "QUEUED_LOCALLY", "receipt": receipt, "visible_in_service": False}
        print(json.dumps(reply, ensure_ascii=False))
        return 0
    except (ContractError, ValueError, OSError, Unavailable) as exc:
        message = exc.as_dict() if isinstance(exc, ContractError) else {"error": type(exc).__name__, "message": str(exc)}
        print(json.dumps(message, ensure_ascii=False), file=sys.stderr)
        return 2


def signals(args) -> list[dict]:
    if args.command == "emit":
        value = json.loads(args.file.read_text())
        return [validate_event(e, args.project) for e in value.get("events", [])]
    if not args.agent:
        raise ContractError("agent_required", "Bind this distinct agent explicitly with --agent; do not inherit a parent's ID")
    if "NATIVE_THREAD_ID" in args.agent:
        raise ContractError("binding_identity", "A placeholder is not a native executor identity")
    def event(kind, payload, nodes=None, edges=None):
        return {"schema": "waypoint.event/1", "event_id": uuid.uuid4().hex, "project_id": args.project, "agent_id": args.agent, "source": "agent-signal", "kind": kind, "at": now(), "node_ids": nodes or [], "edge_ids": edges or [], "payload": payload}
    if args.command == "focus":
        result = [event("scope.set", {}, args.nodes, args.edges)]
    elif args.command == "status":
        result = [event("node.status", {"status": args.text, "explanation": args.why}, [args.node])]
    elif args.command == "done":
        result = [event("node.status", {"status": "done", "explanation": args.result}, [args.node])]
        if args.result or args.diff:
            result.append(event("node.result", {"summary": args.result, "difference": args.diff}, [args.node]))
    elif args.command == "test":
        result = [event("test.result", {"test_id": args.test_id, "run_id": args.run, "outcome": args.outcome, "basis": args.basis, "freshness": "current" if args.current else "unknown"}, [args.node])]
    elif args.command == "note":
        result = [event("item.upsert", {"item_id": "note-" + uuid.uuid4().hex, "type": "agentMessage", "text": args.text, "state": "completed", "authored_note": True}, args.nodes, args.edges)]
    elif args.command == "link":
        result = [event("item.link", {"item_id": args.item}, args.nodes, args.edges)]
    else:
        raise ContractError("command", "Unknown observation command")
    return [validate_event(e) for e in result]


def serve(args):
    import uvicorn
    from .server import create_app
    from .demo import seed
    private_directory(args.data)
    tokens = load_tokens(args.data)
    with (args.data / "service.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ContractError("service_active", "A service already owns this data directory") from exc
        app = create_app(args.data, tokens=tokens)
        if args.demo:
            seed(app.state.store)
        url = f"http://127.0.0.1:{args.port}"
        (args.data / "connection.json").write_text(json.dumps({"url": url}))
        os.chmod(args.data / "connection.json", 0o600)
        print("Open locally (read capability; do not publish): " + url + "/#key=" + tokens["read"], flush=True)
        uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)
    return 0


def rollout_identity(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        line = f.readline(1_000_001)
    if len(line) > 1_000_000:
        raise ContractError("binding_metadata", "Oversized metadata record")
    row = json.loads(line)
    meta = row.get("payload", {})
    if row.get("type") != "session_meta" or not isinstance(meta.get("id"), str):
        raise ContractError("binding_metadata", "Expected session_meta.payload.id")
    return meta


if __name__ == "__main__":
    raise SystemExit(main())
