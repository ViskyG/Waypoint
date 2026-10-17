"""Transactional local event ledger and derived views; no external side effects."""
from __future__ import annotations

import copy
import json
import os
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any

from .domain import ContractError, canonical, descendants, digest, ident, now, plan_diff, three_way, validate_event, validate_plan

DDL = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS plans(version TEXT PRIMARY KEY,project TEXT NOT NULL,ordinal INTEGER NOT NULL,parent TEXT,hash TEXT NOT NULL,at TEXT NOT NULL,body TEXT NOT NULL,UNIQUE(project,ordinal));
CREATE TABLE IF NOT EXISTS heads(project TEXT PRIMARY KEY,version TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS requests(request_id TEXT PRIMARY KEY,hash TEXT NOT NULL,reply TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE NOT NULL,hash TEXT NOT NULL,project TEXT NOT NULL,source TEXT NOT NULL,kind TEXT NOT NULL,agent TEXT,at TEXT NOT NULL,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS event_plan(seq INTEGER PRIMARY KEY,version TEXT);
CREATE INDEX IF NOT EXISTS event_project_seq ON events(project,seq);
CREATE TABLE IF NOT EXISTS agents(project TEXT NOT NULL,id TEXT NOT NULL,body TEXT NOT NULL,PRIMARY KEY(project,id));
CREATE TABLE IF NOT EXISTS scopes(project TEXT NOT NULL,agent TEXT NOT NULL,body TEXT NOT NULL,PRIMARY KEY(project,agent));
CREATE TABLE IF NOT EXISTS items(project TEXT NOT NULL,agent TEXT NOT NULL,id TEXT NOT NULL,first_seq INTEGER NOT NULL,last_seq INTEGER NOT NULL,body TEXT NOT NULL,PRIMARY KEY(project,agent,id));
CREATE INDEX IF NOT EXISTS item_project_first ON items(project,first_seq);
CREATE TABLE IF NOT EXISTS node_states(project TEXT NOT NULL,id TEXT NOT NULL,body TEXT NOT NULL,PRIMARY KEY(project,id));
CREATE TABLE IF NOT EXISTS checks(project TEXT NOT NULL,node TEXT NOT NULL,test TEXT NOT NULL,run TEXT NOT NULL,seq INTEGER NOT NULL,body TEXT NOT NULL,PRIMARY KEY(project,node,test,run));
CREATE TABLE IF NOT EXISTS source_health(project TEXT NOT NULL,source TEXT NOT NULL,body TEXT NOT NULL,PRIMARY KEY(project,source));
CREATE TABLE IF NOT EXISTS cursors(source_key TEXT PRIMARY KEY,body TEXT NOT NULL);
"""


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None, timeout=2)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA busy_timeout=2000")
        self.db.executescript(DDL)
        self.db.execute("INSERT OR IGNORE INTO meta VALUES('schema','1')")
        schema = self.db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()[0]
        if schema not in {"1", "2"}:
            raise ContractError("db_version", "Database schema is newer/incompatible; do not overwrite")
        if schema == "1":
            self._migrate_targets()
        os.chmod(self.path, 0o600)

    def _migrate_targets(self):
        """Schema 1 -> 2, including existing associations, in one transaction."""
        self.db.execute("BEGIN IMMEDIATE")
        try:
            if self.db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()[0] == "2":
                self.db.execute("COMMIT")
                return
            self.db.execute("CREATE TABLE item_targets(project TEXT NOT NULL,agent TEXT NOT NULL,item TEXT NOT NULL,target_kind TEXT NOT NULL,target_id TEXT NOT NULL,first_seq INTEGER NOT NULL,PRIMARY KEY(project,agent,item,target_kind,target_id))")
            self.db.execute("CREATE INDEX target_lookup ON item_targets(project,target_kind,target_id,first_seq DESC,agent,item)")
            for row in self.db.execute("SELECT project,body FROM items").fetchall():
                self._index_item(row["project"], json.loads(row["body"]))
            self.db.execute("UPDATE meta SET value='2' WHERE key='schema'")
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _index_item(self, project: str, item: dict):
        agent, ident = item["agent_id"], item["id"]
        self.db.execute("DELETE FROM item_targets WHERE project=? AND agent=? AND item=?", (project, agent, ident))
        self.db.executemany("INSERT INTO item_targets VALUES(?,?,?,?,?,?)", [
            (project, agent, ident, kind, target, item["first_seq"])
            for kind, field in (("node", "node_ids"), ("edge", "edge_ids"))
            for target in dict.fromkeys(item.get(field, []))
        ])

    def close(self):
        with self.lock:
            self.db.close()

    def _get(self, table: str, columns: tuple[str, ...], values: tuple) -> dict:
        # Table and column names are internal constants, never user input.
        clause = " AND ".join(f"{col}=?" for col in columns)
        row = self.db.execute(f"SELECT body FROM {table} WHERE {clause}", values).fetchone()
        return json.loads(row[0]) if row else {}

    def _put(self, table: str, columns: tuple[str, ...], values: tuple, body: dict):
        cols = ",".join(columns + ("body",))
        self.db.execute(f"INSERT INTO {table}({cols}) VALUES({','.join('?' for _ in range(len(values)+1))}) ON CONFLICT({','.join(columns)}) DO UPDATE SET body=excluded.body", values + (canonical(body),))

    def head(self, project: str) -> str | None:
        with self.lock:
            row = self.db.execute("SELECT version FROM heads WHERE project=?", (project,)).fetchone()
            return row[0] if row else None

    def plan(self, project: str, version: str | None = None) -> dict:
        with self.lock:
            version = version or self.head(project)
            row = self.db.execute("SELECT * FROM plans WHERE project=? AND version=?", (project, version)).fetchone()
            if not row:
                raise ContractError("not_found", "Plan version not found")
            return {"version": row["version"], "ordinal": row["ordinal"], "parent": row["parent"], "at": row["at"], "hash": row["hash"], "plan": json.loads(row["body"])}

    def versions(self, project: str) -> list[dict]:
        with self.lock:
            return [dict(row) for row in self.db.execute("SELECT version,ordinal,parent,hash,at FROM plans WHERE project=? ORDER BY ordinal DESC", (project,))]

    def import_plan(self, proposed: dict, base_version: str | None, request_id: str, merge: bool = False) -> dict:
        ident(request_id, "request_id")
        proposed, warnings = validate_plan(proposed)
        project = proposed["project_id"]
        fingerprint = digest({"plan": proposed, "base": base_version, "merge": merge})
        with self.changed:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                previous = self.db.execute("SELECT hash,reply FROM requests WHERE request_id=?", (request_id,)).fetchone()
                if previous:
                    if previous["hash"] != fingerprint:
                        raise ContractError("idempotency_conflict", "request_id was reused with different input")
                    reply = json.loads(previous["reply"])
                    self.db.execute("ROLLBACK")
                    return reply
                head = self.head(project)
                candidate = proposed
                current = self.plan(project, head) if head else None
                if head != base_version:
                    if not merge or not head or not base_version:
                        raise ContractError("base_conflict", "Plan head moved; read current version", {"current": head, "base": base_version})
                    base = self.plan(project, base_version)["plan"]
                    candidate, conflicts = three_way(base, current["plan"], proposed)
                    if conflicts:
                        raise ContractError("merge_conflict", "Competing plan edits", conflicts)
                    try:
                        candidate, warnings = validate_plan(candidate)
                    except ContractError as exc:
                        raise ContractError("merge_reference_conflict", "Combined update breaks graph references", exc.as_dict()) from exc
                if current and digest(candidate) == current["hash"]:
                    reply = {"version": head, "ordinal": current["ordinal"], "changed": False, "warnings": warnings}
                else:
                    version = "v-" + uuid.uuid4().hex[:16]
                    ordinal = current["ordinal"] + 1 if current else 1
                    self.db.execute("INSERT INTO plans VALUES(?,?,?,?,?,?,?)", (version, project, ordinal, head, digest(candidate), now(), canonical(candidate)))
                    self.db.execute("INSERT INTO heads VALUES(?,?) ON CONFLICT(project) DO UPDATE SET version=excluded.version", (project, version))
                    event = {"schema": "waypoint.event/1", "event_id": "plan:" + request_id, "project_id": project, "source": "waypoint", "kind": "plan.changed", "at": now(), "payload": {"version": version, "parent": head}, "node_ids": [], "edge_ids": []}
                    self._append(event)
                    reply = {"version": version, "ordinal": ordinal, "changed": True, "warnings": warnings}
                self.db.execute("INSERT INTO requests VALUES(?,?,?)", (request_id, fingerprint, canonical(reply)))
                self.db.execute("COMMIT")
            except BaseException:
                if self.db.in_transaction:
                    self.db.execute("ROLLBACK")
                raise
            self.changed.notify_all()
            return reply

    def _append(self, event: dict) -> tuple[int, bool]:
        fingerprint = digest(event)
        old = self.db.execute("SELECT seq,hash FROM events WHERE event_id=?", (event["event_id"],)).fetchone()
        if old:
            if old["hash"] != fingerprint:
                raise ContractError("idempotency_conflict", "event_id was reused with different content")
            return old["seq"], False
        cur = self.db.execute("INSERT INTO events(event_id,hash,project,source,kind,agent,at,body) VALUES(?,?,?,?,?,?,?,?)", (event["event_id"], fingerprint, event["project_id"], event["source"], event["kind"], event.get("agent_id"), event["at"], canonical(event)))
        seq = cur.lastrowid
        self.db.execute("INSERT INTO event_plan VALUES(?,?)", (seq, self.head(event["project_id"])))
        self._project(event, seq)
        return seq, True

    def ingest(self, values: list[dict], cursor: dict | None = None, project: str | None = None) -> dict:
        if not isinstance(values, list) or len(values) > 500:
            raise ContractError("batch_size", "Event batch must contain <=500 entries")
        events = [validate_event(v, project) for v in values]
        with self.changed:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                receipts = [{"seq": seq, "created": created} for seq, created in (self._append(e) for e in events)]
                if cursor is not None:
                    if not isinstance(cursor, dict) or not isinstance(cursor.get("source_key"), str):
                        raise ContractError("cursor", "cursor requires source_key")
                    self.db.execute("INSERT INTO cursors VALUES(?,?) ON CONFLICT(source_key) DO UPDATE SET body=excluded.body", (cursor["source_key"], canonical(cursor)))
                self.db.execute("COMMIT")
            except BaseException:
                if self.db.in_transaction:
                    self.db.execute("ROLLBACK")
                raise
            self.changed.notify_all()
            return {"receipts": receipts, "cursor_saved": cursor is not None}

    def cursor(self, source_key: str) -> dict | None:
        with self.lock:
            row = self.db.execute("SELECT body FROM cursors WHERE source_key=?", (source_key,)).fetchone()
            return json.loads(row[0]) if row else None

    def _project(self, event: dict, seq: int):
        project, agent, kind, payload = event["project_id"], event.get("agent_id"), event["kind"], event["payload"]
        nodes, edges = event["node_ids"], event["edge_ids"]
        capture = self.db.execute("SELECT version FROM event_plan WHERE seq=?", (seq,)).fetchone()
        plan_version = capture[0] if capture else None
        if kind in {"agent.upsert", "agent.activity"}:
            record = self._get("agents", ("project", "id"), (project, agent)) or {"id": agent, "activity": "unknown"}
            if kind == "agent.upsert":
                # Metadata updates cannot smuggle activity changes into the projection.
                for key in ("name", "parent_id", "session_id", "agent_path", "forked_from_id", "provider", "cwd"):
                    if key in payload:
                        record[key] = payload[key]
            else:
                previous_at = record.get("activity_at", "")
                if event["at"] < previous_at or (event["at"] == previous_at and payload.get("historical") and not record.get("activity_historical", False)):
                    return  # Immutable delayed history cannot regress live activity.
                record.update(activity=payload.get("state", "unknown"), activity_at=event["at"], activity_source=event["source"], activity_historical=bool(payload.get("historical")), activity_reported_by=payload.get("reported_by"))
            record["last_seq"] = seq
            self._put("agents", ("project", "id"), (project, agent), record)
        elif kind == "scope.set":
            previous = self._get("scopes", ("project", "agent"), (project, agent))
            if previous and event["at"] < previous["at"]:
                return  # Keep delayed declaration in ledger without regressing active scope.
            # Persist the captured boundary in the ledger too: rebuild must not
            # consult today's source cursor when replaying an earlier focus.
            record = {"agent_id": agent, "node_ids": nodes, "edge_ids": edges, "seq": seq, "at": event["at"], "plan_version": plan_version, "source_boundary": payload.get("source_boundary")}
            self._put("scopes", ("project", "agent"), (project, agent), record)
        elif kind == "item.upsert":
            item_id = payload["item_id"]
            row = self.db.execute("SELECT * FROM items WHERE project=? AND agent=? AND id=?", (project, agent, item_id)).fetchone()
            old = json.loads(row["body"]) if row else {}
            assigned_nodes, assigned_edges = list(nodes), list(edges)
            attribution = "explicit" if nodes or edges else "unassigned"
            if not assigned_nodes and not assigned_edges:
                if old:
                    assigned_nodes, assigned_edges = old["node_ids"], old["edge_ids"]
                    attribution = old["attribution"]
                elif not payload.get("historical"):
                    scope = self._get("scopes", ("project", "agent"), (project, agent))
                    # Late-source data before the focus declaration is not rebound.
                    boundary = scope.get("source_boundary") if scope else None
                    native = "source_revision" in payload
                    after_boundary = not native or (
                        isinstance(boundary, dict)
                        and boundary.get("source_key") == payload.get("source_key")
                        and boundary.get("generation") == payload.get("source_generation")
                        and isinstance(boundary.get("revision"), int)
                        and isinstance(payload.get("source_first_revision"), int)
                        and payload["source_first_revision"] > boundary["revision"]
                    )
                    if scope and event["at"] >= scope["at"] and after_boundary:
                        assigned_nodes, assigned_edges = scope["node_ids"], scope["edge_ids"]
                        attribution = "focus"
            sources = list(dict.fromkeys(old.get("observed_sources", []) + [event["source"]]))
            terminal = {"completed", "done", "failed", "interrupted", "cancelled"}
            older = old and event["at"] < old.get("updated_at", "")
            upgrade = payload.get("state") in terminal and old.get("state") not in terminal
            downgrade = old.get("state") in terminal and payload.get("state") not in terminal
            keep_old = old and not upgrade and (downgrade or older or (payload.get("historical") and not old.get("historical")))
            chosen = {**payload, **old} if keep_old else {**old, **payload}
            state = {**chosen, "id": item_id, "agent_id": agent, "node_ids": assigned_nodes, "edge_ids": assigned_edges, "attribution": attribution, "source": old.get("source", event["source"]) if keep_old else event["source"], "observed_sources": sources, "at": old.get("at", event["at"]), "updated_at": old.get("updated_at", event["at"]) if keep_old else event["at"], "first_seq": row["first_seq"] if row else seq, "last_seq": seq, "plan_version": old.get("plan_version") or plan_version}
            self.db.execute("INSERT INTO items VALUES(?,?,?,?,?,?) ON CONFLICT(project,agent,id) DO UPDATE SET last_seq=excluded.last_seq,body=excluded.body", (project, agent, item_id, state["first_seq"], seq, canonical(state)))
            self._index_item(project, state)
        elif kind == "item.identity_corrected":
            # Explicit correction of an observed provider identity error. The old
            # immutable evidence remains in events; replay applies this correction
            # after it. This never sends anything to the actual executor.
            previous = ident(payload.get("previous_agent_id"), "previous_agent_id")
            item_id = ident(payload.get("item_id"), "item_id")
            if not agent or agent == previous or not isinstance(payload.get("basis"), str) or not payload["basis"]:
                raise ContractError("identity_correction", "A distinct verified actor and evidence basis are required")
            old = self._get("items", ("project", "agent", "id"), (project, previous, item_id))
            current = self._get("items", ("project", "agent", "id"), (project, agent, item_id))
            if not old:
                if current:
                    return
                raise ContractError("item_not_found", "Identity correction targets an unknown item")
            if any(s.startswith("codex-ipc/") for s in old.get("observed_sources", [])):
                raise ContractError("identity_conflict", "Direct native IPC evidence must be reconciled before reassigning this item")
            corrected = dict(current or old)
            audit = list(corrected.get("identity_corrections", []))
            audit.append({"previous_agent_id": previous, "node_ids": old.get("node_ids", []), "edge_ids": old.get("edge_ids", []), "seq": seq, "basis": payload["basis"]})
            corrected.update(agent_id=agent, first_seq=min(old["first_seq"], current.get("first_seq", old["first_seq"])), last_seq=seq, identity_corrections=audit, observed_sources=list(dict.fromkeys(old.get("observed_sources", []) + current.get("observed_sources", []))))
            if not current:
                corrected.update(node_ids=[], edge_ids=[], attribution="unassigned")
            self.db.execute("DELETE FROM item_targets WHERE project=? AND agent=? AND item=?", (project, previous, item_id))
            self.db.execute("DELETE FROM items WHERE project=? AND agent=? AND id=?", (project, previous, item_id))
            self.db.execute("INSERT INTO items VALUES(?,?,?,?,?,?) ON CONFLICT(project,agent,id) DO UPDATE SET first_seq=excluded.first_seq,last_seq=excluded.last_seq,body=excluded.body", (project, agent, item_id, corrected["first_seq"], seq, canonical(corrected)))
            self._index_item(project, corrected)
        elif kind == "item.link":
            row = self.db.execute("SELECT * FROM items WHERE project=? AND agent=? AND id=?", (project, agent, payload["item_id"])).fetchone()
            if not row:
                raise ContractError("item_not_found", "Explicit link targets an unknown item")
            record = json.loads(row["body"])
            record.update(node_ids=nodes, edge_ids=edges, attribution="explicit_correction", last_seq=seq)
            self.db.execute("UPDATE items SET body=?,last_seq=? WHERE project=? AND agent=? AND id=?", (canonical(record), seq, project, agent, payload["item_id"]))
            self._index_item(project, record)
        elif kind in {"node.status", "node.result"}:
            for node in nodes:
                record = self._get("node_states", ("project", "id"), (project, node)) or {"id": node}
                if record.get("at", "") > event["at"]:
                    continue
                if kind == "node.status":
                    record.update(status=payload["status"], explanation=payload.get("explanation", ""), estimate=payload.get("estimate"))
                else:
                    record["result"] = {**payload, "plan_version": payload.get("plan_version") or plan_version}
                record.update(agent_id=agent, at=event["at"], last_seq=seq)
                self._put("node_states", ("project", "id"), (project, node), record)
        elif kind == "test.result":
            for node in nodes:
                record = {**payload, "node_id": node, "at": event["at"], "source": event["source"], "seq": seq, "freshness": payload.get("freshness", "unknown"), "plan_version": payload.get("plan_version") or plan_version}
                self.db.execute("INSERT INTO checks VALUES(?,?,?,?,?,?) ON CONFLICT(project,node,test,run) DO UPDATE SET seq=excluded.seq,body=excluded.body", (project, node, payload["test_id"], payload["run_id"], seq, canonical(record)))
        elif kind == "source.health":
            self._put("source_health", ("project", "source"), (project, payload.get("source_key", event["source"])), {**payload, "at": event["at"], "seq": seq})
        # Unknown kinds remain in the ledger and never become success claims.

    def events_after(self, project: str, after: int = 0, limit: int = 200, wait: float = 0) -> dict:
        limit = min(max(limit, 1), 500)
        with self.changed:
            def read():
                return self.db.execute("SELECT seq,body FROM events WHERE project=? AND seq>? ORDER BY seq LIMIT ?", (project, after, limit)).fetchall()
            rows = read()
            if not rows and wait > 0:
                self.changed.wait(min(wait, 15))
                rows = read()
            return {"events": [{"seq": row["seq"], **json.loads(row["body"])} for row in rows], "cursor": rows[-1]["seq"] if rows else after}

    def items(self, project: str, node: str | None = None, edge: str | None = None, agent: str | None = None, deep: bool = True, before: int | None = None, limit: int = 100, version: str | None = None) -> dict:
        with self.lock:
            scope = descendants(self.plan(project, version)["plan"], node) if node and deep else {node} if node else None
            page_size = min(max(limit, 1), 500)
            # Read target associations before fetching any message body. Each
            # bounded chunk returns only its newest page; union preserves global
            # receipt order without JSON extensions or parameter-limit assumptions.
            targets = sorted(scope) if scope is not None else None
            chunks = [targets[i:i + 350] for i in range(0, len(targets), 350)] if targets is not None else [None]
            candidates = {}
            for chunk in chunks:
                values = [project]
                if chunk is not None or edge:
                    clause = "t.project=?"
                    if chunk is not None:
                        clause += " AND t.target_kind='node' AND t.target_id IN (" + ",".join("?" for _ in chunk) + ")"
                        values.extend(chunk)
                    else:
                        clause += " AND t.target_kind='edge' AND t.target_id=?"
                        values.append(edge)
                    if edge and chunk is not None:
                        clause += " AND EXISTS(SELECT 1 FROM item_targets e WHERE e.project=t.project AND e.agent=t.agent AND e.item=t.item AND e.target_kind='edge' AND e.target_id=?)"
                        values.append(edge)
                    if agent:
                        clause += " AND t.agent=?"; values.append(agent)
                    if before is not None:
                        clause += " AND t.first_seq<?"; values.append(before)
                    query = "SELECT DISTINCT t.agent,t.item AS id,t.first_seq FROM item_targets t WHERE " + clause
                else:
                    clause = "project=?"
                    if agent:
                        clause += " AND agent=?"; values.append(agent)
                    if before is not None:
                        clause += " AND first_seq<?"; values.append(before)
                    query = "SELECT agent,id,first_seq FROM items WHERE " + clause
                for row in self.db.execute(query + " ORDER BY first_seq DESC LIMIT ?", (*values, page_size + 1)):
                    candidates[(row["agent"], row["id"])] = dict(row)
            ordered = sorted(candidates.values(), key=lambda r: r["first_seq"], reverse=True)
            more = len(ordered) > page_size
            selected = ordered[:page_size]
            found = [self._get("items", ("project", "agent", "id"), (project, row["agent"], row["id"])) for row in selected]
            cursor = self.db.execute("SELECT COALESCE(MAX(seq),0) FROM events WHERE project=?", (project,)).fetchone()[0]
            return {"items": list(reversed(found)), "before": found[-1]["first_seq"] if found and more else None, "has_more": more, "cursor": cursor}

    def projects(self) -> list[dict]:
        with self.lock:
            return [{"project_id": row["project"], "version": row["version"], "title": json.loads(row["body"])["title"]} for row in self.db.execute("SELECT h.project,h.version,p.body FROM heads h JOIN plans p ON h.version=p.version ORDER BY h.project")]

    def state(self, project: str, version: str | None = None) -> dict:
        with self.lock:
            plan = self.plan(project, version)
            def all_rows(table):
                return [json.loads(row[0]) for row in self.db.execute(f"SELECT body FROM {table} WHERE project=?", (project,))]
            agents, scopes, statuses = all_rows("agents"), all_rows("scopes"), all_rows("node_states")
            checks = all_rows("checks")
            latest: dict[tuple, dict] = {}
            for check in checks:
                key = (check["node_id"], check["test_id"])
                if key not in latest or latest[key]["seq"] < check["seq"]:
                    latest[key] = check
            recent = self.items(project, limit=500)["items"]
            refs = set()
            for record in scopes + statuses:
                refs.update(record.get("node_ids", [record["id"]] if "id" in record else []))
            ghosts = {}
            for ref in refs - set(plan["plan"]["nodes"]):
                for old in self.db.execute("SELECT version,body FROM plans WHERE project=? ORDER BY ordinal DESC", (project,)):
                    historical = json.loads(old["body"])["nodes"].get(ref)
                    if historical:
                        ghosts[ref] = {**historical, "retired": ref not in self.plan(project)["plan"]["nodes"], "absent_from_view": True, "from_version": old["version"]}; break
            seq = self.db.execute("SELECT COALESCE(MAX(seq),0) FROM events WHERE project=?", (project,)).fetchone()[0]
            return {**plan, "current_version": self.head(project), "agents": agents, "scopes": scopes, "node_states": statuses, "checks": list(latest.values()), "items": recent, "ghosts": ghosts, "sources": all_rows("source_health"), "cursor": seq, "warnings": validate_plan(plan["plan"])[1]}

    def diff(self, project: str, before: str, after: str) -> list[dict]:
        return plan_diff(self.plan(project, before)["plan"], self.plan(project, after)["plan"])

    def backup(self, destination: str | Path):
        with self.lock:
            other = sqlite3.connect(str(destination))
            try:
                self.db.backup(other)
            finally:
                other.close()
            os.chmod(destination, 0o600)

    def rebuild(self) -> dict:
        """Rebuild only disposable projections from the immutable accepted ledger.

        External sources are not touched. Capture-version records keep old acceptance
        and attribution context independent of today's head. Cursors stay unchanged.
        """
        with self.changed:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                for table in ("agents", "scopes", "items", "item_targets", "node_states", "checks", "source_health"):
                    self.db.execute(f"DELETE FROM {table}")
                count = 0
                for row in self.db.execute("SELECT seq,body FROM events ORDER BY seq").fetchall():
                    self._project(json.loads(row["body"]), row["seq"])
                    count += 1
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
            self.changed.notify_all()
            return {"replayed": count, "external_sources_read": False}
