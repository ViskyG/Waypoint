"""Loopback API. Browser capability is read-only; no agent-control routes exist."""
from __future__ import annotations
import asyncio
import secrets
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .domain import ContractError
from .security import load_tokens
from .spool import drain
from .store import Store

WEB = Path(__file__).parent / "web"


def create_app(data_dir: Path, tokens: dict | None = None, testing: bool = False) -> FastAPI:
    tokens = tokens or load_tokens(data_dir)
    store = Store(data_dir / "waypoint.db")

    @asynccontextmanager
    async def lifespan(app):
        async def flush():
            while True:
                try:
                    await asyncio.to_thread(drain, data_dir, store)
                    app.state.outbox_error = None
                except (OSError, RuntimeError, sqlite3.Error) as exc:
                    app.state.outbox_error = type(exc).__name__  # evidence remains in the outbox; no agent is interrupted
                await asyncio.sleep(1)
        worker = asyncio.create_task(flush())
        try:
            yield
        finally:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
            store.close()

    app = FastAPI(title="Waypoint local observation API", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.store = store
    app.state.tokens = tokens

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        host = request.url.hostname
        allowed = {"127.0.0.1", "localhost", "::1"} | ({"testserver"} if testing else set())
        if host not in allowed:
            return JSONResponse({"error": "host_denied"}, status_code=403)
        origin = request.headers.get("origin")
        if origin:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or parsed.netloc != request.headers.get("host"):
                return JSONResponse({"error": "origin_denied"}, status_code=403)
        if request.url.path.startswith("/api/"):
            token = request.headers.get("authorization", "").removeprefix("Bearer ")
            write = secrets.compare_digest(token, tokens["write"])
            read = secrets.compare_digest(token, tokens["read"])
            if not (write or (read and request.method in {"GET", "HEAD"})):
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        if request.method in {"POST", "PUT", "PATCH"}:
            chunks, count = [], 0
            async for chunk in request.stream():
                count += len(chunk)
                if count > 8_000_000:
                    return JSONResponse({"error": "body_too_large"}, status_code=413)
                chunks.append(chunk)
            request._body = b"".join(chunks)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ContractError)
    async def contract_error(request, exc: ContractError):
        status = 404 if exc.code in {"not_found", "item_not_found"} else 409 if "conflict" in exc.code else 422
        return JSONResponse(exc.as_dict(), status_code=status)

    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html")

    app.mount("/static", StaticFiles(directory=WEB), name="static")

    @app.get("/api/health")
    def health():
        return {"service": "waypoint", "version": "0.1.0", "observer_only": True, "outbox_error": getattr(app.state, "outbox_error", None)}

    @app.get("/api/projects")
    def projects():
        return store.projects()

    @app.get("/api/p/{project}/state")
    def state(project: str, version: str | None = None):
        return store.state(project, version)

    @app.get("/api/p/{project}/versions")
    def versions(project: str):
        return store.versions(project)

    @app.get("/api/p/{project}/plan")
    def plan(project: str, version: str | None = None):
        return store.plan(project, version)

    @app.get("/api/p/{project}/diff")
    def diff(project: str, before: str, after: str):
        return {"changes": store.diff(project, before, after)}

    @app.get("/api/p/{project}/items")
    def items(project: str, node: str | None = None, edge: str | None = None, agent: str | None = None, deep: bool = True, before: int | None = None, limit: int = 100, version: str | None = None):
        return store.items(project, node, edge, agent, deep, before, limit, version)

    @app.get("/api/p/{project}/events")
    def events(project: str, after: int = 0, limit: int = 200, wait: float = 0):
        return store.events_after(project, after, limit, wait)

    @app.get("/api/cursor")
    def cursor(source_key: str):
        return store.cursor(source_key) or {}

    @app.get("/api/p/{project}/packet/{node_id:path}")
    def packet(project: str, node_id: str):
        document = store.plan(project)
        graph = document["plan"]
        if node_id not in graph["nodes"]:
            raise ContractError("not_found", "Block not found")
        node = graph["nodes"][node_id]
        return {"project_id": project, "plan_version": document["version"], "node_id": node_id, "assignment": node["assignment"], "acceptance": node["acceptance"], "tests": node["tests"], "source_refs": node.get("source_refs", []), "predecessors": [e["from"] for e in graph["edges"].values() if e["to"] == node_id], "children": [k for k, n in graph["nodes"].items() if n.get("parent") == node_id]}

    @app.post("/api/p/{project}/events")
    def ingest(project: str, body: dict):
        return store.ingest(body.get("events", []), body.get("cursor"), project)

    @app.post("/api/p/{project}/plans")
    def import_plan(project: str, body: dict):
        if body.get("plan", {}).get("project_id") != project:
            raise ContractError("project_mismatch", "Plan is for another project")
        return store.import_plan(body["plan"], body.get("base_version"), body.get("request_id", ""), bool(body.get("merge")))

    return app
