# Waypoint contracts 1.0

This file specifies the chosen design. Implemented reference contracts live in `waypoint/domain.py`, `store.py` and `server.py`; `schemas/` supplies interchange validation. The renderer is not the authority for these contracts. Any extension must preserve the observer-only boundary.

## 1. Identity and versions

`project_id` identifies one local map namespace and is a URL-safe single path segment. It is not a filesystem path or a remote repository. Nodes and edges have immutable IDs scoped to that project; use readable `W-02` / `E-01` IDs and never recycle an ID for unrelated work. Titles may change independently. Hierarchical IDs such as W-02.1 help navigation but do **not** determine parentage: `parent` does.

An agent ID is `provider/native-thread-id` in the current single-local-installation scope. For tested Codex input the native value is **payload.id**, not shared `session_id`. Preserve parent thread ID, shared container session, task/agent path and fork ancestry separately. Additional hosts/installations must add an installation namespace before importing into the same store. The initial implementation never merges remote installations.

A plan version is an opaque `v-…` ID allocated by the store; ordinal is a display label, not a concurrency token. Event sequence is local receipt/commit order, not a claim of global chronological causality. `at` is a source timestamp with timezone, normalized to UTC. Source-native times and observer-arrival times should not be compared as precise physical latency without a measured common clock. The current recorder distinguishes historical hydration; unknown provider timestamps use an explicit epoch sentinel and must not be described as recent work.

## 2. Plan interchange

```json
{
  "schema": "waypoint.plan/1",
  "project_id": "example",
  "title": "Example work",
  "nodes": {
    "W-01": {
      "title": "Export",
      "parent": null,
      "assignment": "Export selected records without changing the source.",
      "acceptance": {"A-01": {"text": "Columns and values match the selected input."}},
      "tests": {"T-01": {"label": "Empty input"}},
      "layout": {"x": 80, "y": 100},
      "source_refs": []
    }
  },
  "edges": {}
}
```

Draft nodes may be incomplete in storage; the map-authoring skill creates meaningful assignments and acceptance criteria. No hidden `approved`, `ready`, `done` requirement is inserted into the plan schema. Tests are independently named planned checks, not one test per code edit.

Structural invariants: every parent and edge endpoint exists in the submitted snapshot; parentage is acyclic; IDs are unique dictionary keys; coordinates are finite; the JSON is size-bounded. Dependency cycles produce diagnostics and remain visible rather than prohibiting real work. Runtime observations may reference unknown/retired blocks even though a structural edit may not introduce a broken parent pointer.

## 3. Atomic plan update

`POST /api/p/{project}/plans` takes:

```json
{"request_id":"a-stable-operation-id","base_version":"v-observed-head","merge":true,"plan":{"schema":"waypoint.plan/1","project_id":"example","title":"Example work","nodes":{},"edges":{}}}
```

A first import declares `base_version:null`. A retry reuses **both** request ID and identical body. Same ID/different content is 409 `idempotency_conflict`; moved head without merge is 409 `base_conflict`. With merge enabled, compare base/current/proposed recursively by keyed fields. Identical edits merge; disjoint fields merge; unequal concurrent field edits conflict; deletion versus an edited object conflicts. Lists are atomic. Validate the merged graph: deletion versus a newly added reference becomes `merge_reference_conflict`. No partial graph is installed on error. A no-op returns the existing version. Failed imports do not enter an asynchronous outbox.

A full proposed snapshot is chosen for v1 interchange. Agents may edit a small owned file and resubmit it; they need not narrate the full plan. A future patch endpoint can share this same transaction/merge engine. Do not confuse the private IPC patch format with public plan mutations.

`plan-export` creates a new file containing `{base_version, plan}` and refuses implicit overwrite. Git commit/push remains the existing project's explicit workflow. Waypoint does not invoke Git or overwrite a project tree. Plan content can itself contain sensitive requirements: exclusion of runtime logs is not universal sanitization of a public release.

## 4. Observation envelope

```json
{
  "schema":"waypoint.event/1",
  "event_id":"receipt-stable-across-retry",
  "project_id":"example",
  "source":"agent-signal",
  "agent_id":"codex/distinct-native-id",
  "at":"2026-10-16T12:00:00Z",
  "kind":"scope.set",
  "node_ids":["W-01","W-02"],
  "edge_ids":[],
  "payload":{}
}
```

Required: event ID, project, source, timestamp, kind and object payload. The API supplies empty reference lists when omitted. IDs, payload size and types are validated. Unknown `kind` values are stored without becoming invented status changes. One event may refer to several nodes/edges. Unknown work references are valid observations, not rejected plan edits.

A batch contains at most 500 events, bounded by 8 MB HTTP body and 3 MB per serialized event. These are protective reference defaults, not a throughput/SLA claim. With a source cursor, **all** events/projections/cursor are committed in one transaction. On failure none advance. A durable receipt distinguishes newly accepted versus identical replay. Cursor records are project/source-specific; they cannot establish recovery of events never emitted or observed.

### Event semantics

| Kind | Payload | Effect |
|---|---|---|
| `agent.upsert` | name, parent_id, session_id, agent_path, forked_from_id, provider | Metadata only; does not make agent active. |
| `agent.activity` | state, reported_by, historical, turn_id | Observed provider activity, never inherited from parent. Per-native rollout task_started means running and task_complete means idle; these never mean plan done. Older history cannot replace newer IPC activity. |
| `scope.set` | optional source_boundary | Replace that agent's current set of associated nodes/edges, not an exclusive claim. Empty set releases association. |
| `item.upsert` | item_id, type, text, state, historical, content_origin | Update one native item projection; keep immutable received evidence. subAgentActivity retains its original kind, agent_thread_id and agent_path; missing visible text is not summarized. |
| `item.identity_corrected` | item_id, previous_agent_id, basis | Explicit evidence-backed native actor correction; move/merge projection and target index transactionally, preserve first_seq and immutable old evidence. Conflicting direct IPC ownership is rejected. |
| `item.link` | item_id | Explicitly correct associations to envelope node/edge references. |
| `node.status` | status, explanation, optional estimate | Free text declaration. No transition enum/gate. |
| `node.result` | summary, difference, optional plan_version | Result and expected/actual discrepancy; does not rewrite acceptance. |
| `test.result` | test_id, run_id, outcome, basis, freshness | One actual check result, independent of node status. |
| `source.health` | source_key, state, detail | Observation channel health, not agent completion. |

Test outcomes use a small machine vocabulary (`passed`, `failed`, `skipped`, `error`, `not_run`) because lamps need distinct meaning. This does **not** turn the owner's free-form work status into an enum. `freshness:current` requires a stated basis, but is still an evidence assertion, not automatic proof that all current code is covered. Unknown is the default; the test UI exposes basis/age/version separately in the designed full view.

## 5. Attribution and ordering

Explicit item references take priority. Otherwise the first nonhistorical sighting may inherit the agent's current focus when its observed timestamp is not earlier than the focus boundary. Once bound, later item revisions retain the initial association. An explicit correction changes the association while retaining evidence of that correction. Hydrated old items are unassigned unless they already have an established association.

Focus signals capture the committed native cursor as `source_boundary:{source_key,generation,revision}`. Native items carry `source_key`, `source_generation`, `source_first_revision`, and `source_revision`. Only a first sighting newer than that boundary, in the same source generation and not predating the focus timestamp, can inherit focus. Missing boundaries, generation changes, historical hydration and straddling items stay unassigned; later revisions preserve the first association. Explicit corrections remain available. This is a conservative attribution contract, not a claim of distributed causality. Parent scopes must not be blindly inherited into children. Before emitting a signal, the executor binding must be established from that distinct thread's provider metadata. Shared container session IDs cannot substitute. Until a verified binding exists, preserve the live transcript as unassigned rather than guess the agent. This is a required integration seam, not a second observer or a request for new architectural discovery.

`item_id` reconciliation is exact when native IDs agree. An unidentified JSONL message gets a source-location identity, not a text hash. Repeated identical messages are legitimate. If native identifiers cannot reconcile two representations, retain both with source provenance; do not claim perfect cross-source deduplication.

Terminal native item states cannot be regressed to running by delayed hydration. Old historical text does not overwrite a newer live result. Immutable source observations remain available even when the current projection prefers the newer item. Delayed scope/status signals do not overwrite newer timestamps. These are same-host conservative rules, not distributed-clock consensus.

## 6. Read API

Every `/api/` call requires `Authorization: Bearer <local capability>`. Read key permits GET/HEAD only, write key permits observation/plan writes. Browser holds only a read key from a URL fragment, removes it from the address and stores it within the tab. Never put that key in a public screenshot or logs. HTTP is restricted to loopback and matching Origin/Host.

| GET route | Returned information |
|---|---|
| `/api/health` | Service version, observer-only declaration, outbox error category. |
| `/api/projects` | Registered project IDs, titles and plan heads. |
| `/api/p/{project}/state?version=...` | Consistent plan + current agent/scopes/items/status/checks/ghosts/source health. Old plan is explicitly **not** old-time playback. |
| `/api/p/{project}/versions` | Immutable version metadata. |
| `/api/p/{project}/plan?version=...` | Exportable versioned plan. |
| `/api/p/{project}/diff?before=...&after=...` | Deterministic keyed-field structural differences. |
| `/api/p/{project}/items?node=...&deep=true&before=...&limit=100` | Paged original item projections; filters also accept edge or agent. |
| `/api/p/{project}/events?after=...&wait=12&limit=200` | Committed notifications for incremental refresh; no token in URL. |
| `/api/p/{project}/packet/{node_id}` | Compact assignment, acceptance, tests, predecessors and children for the executor. |
| `/api/cursor?source_key=...` | Last accepted source checkpoint. |

Item pages preserve ascending `first_seq` order within the newest selected window. `before` is an exclusive stable first-receipt cursor, returned only when more items exist; revisions do not move an item between pages. Additive `cursor` is the latest committed project event sequence at that read. Schema 2 indexes node/edge associations in `item_targets`; selection resolves target keys before loading message bodies, with descendant IDs chunked at 350. Association updates, item revisions and explicit links share the ledger transaction. Schema 1 migration backfills associations once; reopen and projection rebuild retain order. No optional SQLite JSON functions are required.

## 7. Private IPC profile

Source: owner's P09 script and tested extension build, not an official public OpenAI protocol. Frames: uint32 little-endian length + JSON. Outgoing allowlist: initialize, owner discovery, complete-history load, follow/unfollow, and discovery response `canHandle:false`. No user-supplied arbitrary RPC, no resume/start/steer/approval/stop.

State snapshots carry a revision; patches carry baseRevision, revision and **array paths** of object keys/list indices. Supported operations are add/remove/replace. Apply a whole patch batch to an isolated candidate; one bad operation leaves the last good state intact. A revision gap invalidates freshness and requests hydration. Socket ownership/peer UID is checked. Frame size and parsing depth/traversal have explicit protection; over-budget or incompatible frames produce source-health errors, never new execution permission.

The collector is a separate foreground process from the UI/API so decoding cannot block the browser server event loop. It shares the single ledger through authenticated local requests. It discovers only the selected thread family from first-line metadata and never launches agents. On failed commit or disconnection, stop that live projection, reconnect with backoff and hydrate. File offsets advance only with committed events. No global Codex config, auth file, running session or hooks are modified.
