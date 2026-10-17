# Waypoint next stage — readable work and inspectable logic

Status: detailed design; not installed runtime. Resource policy: MIXED. Existing Codex-oriented execution can complete the whole project. Chat capsule supply remains OPTIONAL; no new dependency on a chat finishing is introduced.

## 1. Product invariant
One project work graph, several human views, and one evidence ledger. A user should understand what is changing, why it matters, what is actually happening, which real inputs are missing and which custom logic needs review. Waypoint observes; it never becomes the authority granting agents permission to work.

A readable task description is not a shortened file-edit instruction. Both can be necessary, but they have different readers. The project plan and a block's human description share authored intent; live status is joined by stable project/node identity, not written again for the plan.

## 2. Navigation and project boundary
Home is `Projects`. It lists already registered projects from existing `/api/projects`, not arbitrary filesystem repositories. Each card shows name, purpose, active work count, last observed activity and source-health age. Counts are derived from runtime data; do not invent a project percentage from an arbitrary mix of packets, subtasks and tests. Keep a compact top project switcher, but it is not the catalogue itself.

Inside a project use `Map | Plan | Algorithms`; existing agents/orchestrators and inspectors remain available. Links include project_id, view, node/algorithm ID and optional plan version. Same node ID in two projects is two different identities. UI caches, selected node, filters, camera and scroll state are keyed accordingly.

Switching projects increments a request-generation token and aborts old fetches/long polls where possible. A response is applied only if project and generation still match. Preserve current local-only authorization: an existing service-wide read token is not suddenly presented as per-project security. Do not broaden a restricted installation's accessible project list. Do not send raw messages to the catalogue.

## 3. Block task: Human first, executor detail second
The `Task` tab opens `What and why` by default. Its content is authored once as intent:
- short outcome summary, used verbatim in the project plan;
- project context / why this work exists;
- observable before → after;
- approach and scope when needed to explain the mechanism, without edit commands.
A second subtab `For the executor` exposes the existing assignment, precise reading set, owned paths, contracts and technical checks. Existing acceptance remains a separate right-side surface. Links to source code are useful there, but cannot substitute for the human explanation.

Example C05.2: "New messages and command results should reach the map without repeatedly rebuilding the whole conversation. The observer will process only changed items and remember what is durably stored. This keeps long sessions responsive and prevents a reconnect from silently losing updates." Executor detail still names normalizer, dirty item indexes, cursor receipts, files and tests.

Keep node.assignment as the existing execution contract for compatibility. Add `node.x_observability.intent`; this avoids breaking existing Codex packet consumers. The UI must not silently substitute the opaque assignment when intent is absent. For an old block show `Human description not prepared` and leave the technical subtab accessible. Migration supplies reviewed human descriptions for existing nodes; there are no runtime LLM summaries.

## 4. Project Plan: a view, not a second document to maintain
Render a readable nested outline from node title + intent.summary + explicit parent/order. Display group purpose and all currently planned work, with expandable detail for larger maps. A flat sequence is not implied: parallel branches remain visibly parallel and prerequisites are labelled.

Each row reads the SAME reported status, observed activity, test freshness and warning projection as its graph node. Updating one block event updates both. Clicking a row focuses the block; returning to the plan restores the reader's position. Filtering the outline affects display only, not graph content or completion counts.

For containers show `reported: waiting; inside: 2 active, 1 result available` when these differ. Never silently rewrite the agent's status to done, nor show a parent as apparently idle simply because children were not reported to that ID. Any aggregate progress is identified as derived and counts unique execution leaves or explicitly weighted deliverables; parent and child are not counted twice. Tests passed is not work completed.

The historical plan selector remains a plan snapshot selector. Until historical runtime replay is implemented, clearly label accompanying statuses as current observations associated with a historical structure. Never imply they were the status at that old time.

## 5. Dependency semantics and the reported anomaly
Use hard blocker edges ONLY for a necessary input/result. Author must answer: "What exact result from A is required for which part of B, and what observation establishes availability?" Adjacency, nice left-to-right drawing, common file ownership or a preferred coding sequence are not sufficient reasons for a hard edge.

An edge contains a readable reason, required output/acceptance reference, start-versus-finish phase, and target scope (node or subtree). A desired order is a separate `order` relation, rendered differently and excluded from hard readiness. Shared-file ownership constrains executor concurrency, not domain input availability; record it in work ownership, not by pretending the code result is needed.

C05.3 provides the indexed read contract needed by C06.3's assembled browser check. That edge must target C06.3. C06.1's client-side reading model can be prepared using the stable contract independently. A collapsed arrow shows `partial dependency` and its true endpoints, not `all C06 waits for all C05`.

One shared pure prerequisite resolver supplies authoring validation, `/packet`, frontier reporting and UI. It considers explicit ancestor/subtree applicability. Do not maintain separate implementations in the CLI, planner and browser. Validate the effective graph after inheritance (including hidden self-dependencies), not only its raw edges. Child completion is not a requirement to enter its own parent container.

Availability is separate from freeform status: `satisfied | missing | unknown | waived` with evidence/provenance, requirement revision and timestamp. These are dependency evaluations, NOT an enum replacing the user's statuses. `done` alone does not prove that the required artifact/contract is available in the consumer workspace. An existing valid artifact may satisfy the input while the producing block's status remains stale. A changed requirement invalidates earlier satisfaction evidence; a cosmetic plan layout change does not automatically invalidate it.

Waypoint accepts observations of early work and displays `started without confirmed prerequisite`, showing which condition and evidence are missing. It does not reject telemetry, pause the agent, or manufacture completion of the predecessor. The executor's normal workflow should check actual necessary inputs, revise an inaccurate edge, or record a justified deviation; it need not ask the viewer's permission. Delayed evidence can resolve an unknown without rewriting history.

The specific owner's incident remains unassigned to a cause until real IDs/version/observations are supplied. Source inspection DID identify the direct-only `/packet` versus ancestor-aware offline frontier mismatch. That seam is included as a regression, not asserted to be the unique cause.

## 6. Message filters
Reuse the old Observer's independent per-reader filter behaviour, without control commands. New multi-select facets: messages, visible reasoning/explanations, plan, commands, command results when separable, file changes, tests, errors, agent/lifecycle events, other/unknown. Always retain the native type next to the normalized category in detailed inspection.

The old source dropdown actually has all/reasoning/message/command/diff/control/error/protocol. Additional new facets are an explicit Waypoint extension. A combined command/result item is not two independent executions. If the provider exposes distinct parts, render selectable facets referencing one original item; otherwise keep a labelled combined card. A hidden reasoning field is not reconstructed. Empty/unavailable categories are labelled, not silently populated.

Filter per block-card reader or inspector; an optional project default initializes new readers. User choice lives in viewer preferences, not a plan mutation or agent instruction. OR within selected types; AND with existing agent/search/scope. Deep streams deduplicate a source item associated with multiple descendants. Badge counts distinguish filtered/new visible items from total unseen items.

Apply filtering BEFORE page limits and cursor selection. Filtering only the newest 500 cached items can hide matching older messages incorrectly. Extend `/items` with type selection, indexed categories where useful and filter-aware cursors. Cursor is tied to project, plan-view scope, type selection and ordering; a changed filter starts a new window. Preserve selected text and stable scroll anchors; new matching messages show a count rather than dragging the reader to the bottom. Source events continue to be ingested regardless of filters. Unknown types survive under Other.

## 7. Algorithm records: controlled custom logic, not a technology inventory
An algorithm record represents a meaningful custom transformation, selection, scheduling, merging, layout, recovery or optimization mechanism whose correctness or cost warrants independent inspection. A thin call to a library, framework choice or CRUD wrapper alone is not a record. A custom batched fetch with pagination, retries, deduplication and bounded memory can qualify even when it uses libraries.

Author one project-level record per mechanism, referenced from all relevant blocks. The block badge shows direct algorithm count; a separate descendant count may be offered. Clicking it opens the existing RIGHT inspector filtered to that block's algorithms. A project Algorithms view shows the same records, not copies.

Minimal record: stable ID/name; purpose in product terms; inputs/outputs; strategy; invariants and edge cases; implementation references (repository-relative path + symbol + revision, null while planned); testability strategy and actual test/evidence references; known computational/resource risks. Evidence is optional when not yet collected, and absence is explicit. A missing record is not evidence that the block has no custom algorithms; use reviewed / not reviewed inventory metadata only where needed.

For optimization record the hypothesis and constraint, old/new implementation revisions, correctness check and measurement evidence. Measurements identify input/data scale, environment/runtime, metric/unit, method/sample count and actual result. Comparisons require compatible datasets, semantics and method; otherwise show `not comparable`, not a green speedup. Record memory/I/O and correctness trade-offs where material. Code or invariant changes mark affected evidence stale, not failed. Existing test runs should supply evidence; do not run a benchmark or ask the model to write a summary on each ordinary edit.

Initial useful Waypoint examples: conservative three-way graph merge; item-target pagination; effective-prerequisite resolution; anchored incremental chat reconciliation. Use source references to the inspected commit. A framework name (FastAPI, SQLite, SVG) is not substituted for any of these mechanisms.

Do not embed copied source code permanently in the plan. Resolve exact safe repository references or show a snapshot explicitly labelled with its revision; never eval snippets or auto-run test commands from this panel. Runtime evaluation events link to the record, node(s), implementation revision and test/baseline receipts. The algorithm definition and its observed evidence remain separate.

## 8. Data contract and migration
Keep the existing `waypoint.plan/1` transport. Add versioned `x_observability` profile metadata for intent, typed dependency evidence contracts and algorithm records. Existing schema/storage preserves extensions; old clients DO NOT implement the new views merely because import succeeds. Expose a feature/profile capability in the updated service and report unsupported semantics at handoff.

Do not overwrite the current head with the old source ZIP. Start from a fresh plan export and current runtime/code; preserve all IDs, source events, statuses, unknown extension keys and result references. Add human intent; keep assignment and actual test history. New dependency conditions need review against actual artifacts, not guessed status conversion. Readiness for an unclassified legacy edge is unknown until classified, with its previous link kept visible.

One consistent state revision/cursor feeds Map and Plan; catalogue has a bounded metadata-only summary. Extend rather than replace existing project/target indexes. Algorithm definitions belong to plan snapshots; mutable implementation/evaluation observations use the event ledger. Requirements revision fingerprints exclude layout and prose formatting changes that do not alter the predicate. Import guards use current base_version/request_id; migration is idempotent and reversible by restoring the previous plan version (not deleting evidence).

## 9. Three selected styles
Maintain an extensible theme registry rather than a binary toggle. Terracotta and Obsidian remain concrete, verified references. A third selected slot is `awaiting_reference` until its distinct intended appearance is recoverable. Two of the three accessible attachments have identical bytes; this is an evidence gap, not a change to the requirement. Do not ship the third slot as a duplicate and report three completed designs. Theme accents never replace status/test semantics.

## 10. Bounded next implementation
N01 contracts/migration → N02 dependency resolver and N03 catalogue/plan/task UX can develop against stable N01 contracts. N04 typed stream retrieval/UI and N05 algorithm catalogue also depend on N01. N06 theme registry is independent at the token/asset level but joins the single UI in the integration order. N07 integrates and tests the entire changed cycle. Detailed responsibilities and exact entry/exit outputs are in WORK_PACKETS.md.

No new orchestrator, agent control panel, parallel writable roadmap, forced capsule scheduling or paid model turn is introduced. Existing Codex observations continue during viewer evolution. Only the theme-specific acceptance remains waiting for the third reference; independent design and implementation may proceed.
