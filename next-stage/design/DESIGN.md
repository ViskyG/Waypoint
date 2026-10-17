# Next-stage design — readable work, real prerequisites, inspectable algorithms

This document and CONTRACTS.md complete the earlier conceptual brief. They are
implementation requirements for the next Codex run, NOT evidence of deployed
features. Existing runtime/source baseline is in sources/BASELINE.json. Earlier
briefs are preserved under sources/prior-brief for provenance, not competing specs.
Where they leave syntax open, the contracts in THIS delivery prevail. All owner
requirements remain, including three themes and optional chat execution.

<a id="d1"></a>
## D1. One system and one graph
Keep the current local Python/FastAPI/SQLite service, native IPC/rollout collectors,
and browser UI. Add read views and evidence contracts; do not rebuild the collector
or introduce a new orchestrator, database service, timeline engine or work queue.
Runtime metadata is already project-scoped. The state ledger supplies both Map and
Plan. The catalogue reads bounded summaries, not every transcript. New source events
remain accepted even when they describe work before a prerequisite is confirmed.

<a id="d2"></a>
## D2. Reader intent versus execution assignment
`node.x_observability.intent` contains summary, context, change and optional scope.
The summary is an outcome in ordinary project language, not a path/function list.
Context explains why the block exists; change explains observable before/after.
Keep `node.assignment`, source_refs and x_roadmap's reading/ownership information
as the executor contract. The Task panel opens Human intent first and has a separate
For executor subtab. Acceptance remains the right-side expected/actual surface.

The Plan outline displays the same summary and can expand the same intent; it
never separately paraphrases or stores its own descriptions/statuses. Existing
blocks missing intent show an explicit incomplete-description indication and a
technical subtab, not a fake model-generated explanation. Backfill current Waypoint
nodes once during an authoring revision; never generate summaries at view time.
Example: “Keep the place I am reading when a new agent message arrives” is the
user outcome; “key DOM by project/agent/item and preserve scroll anchor” belongs
in execution detail. Technical descriptions remain accessible, not discarded.

<a id="d3"></a>
## D3. Catalogue, project navigation and Plan
Default home is Projects. Show name, purpose, active distinct agents/blocks,
source health/age and last observed activity. Do not infer completion percentages
from mixed packets/children/tests. Keep the existing compact project switcher.
Within a project: Map | Plan | Algorithms. Selecting a plan row focuses its block;
back restores the previous outline position and expanded items. Outline covers
all meaningful groups and blocks, not only currently visible graph nodes.

Parent status is what was reported to that parent. Add an independent descendant
activity summary; never overwrite its status because a child is active or done.
A stale parent can read “reported: waiting; inside: two active”. Count distinct
actors and distinct leaves, never one parent plus its children as extra work.
For an old plan version label runtime values as current observations over a past
structure; historical runtime replay is outside this stage.

UI preferences/caches are keyed by service + project + view + selected plan scope.
Increment a request-generation on every navigation that changes the project;
abort stale requests and discard late responses unless generation/project match.
A shared read token still authorizes the same service; a catalogue is not a new
claim of per-project security. Do not enumerate arbitrary filesystem projects.

<a id="d4"></a>
## D4. Dependency semantics without execution control
An execution blocker needs a producer result, a consumer and an availability
condition. Coding preference, drawn proximity and file conflicts are not blocker
edges. `requires` edges carry a condition and start/finish phase; `order` edges
are dashed optional ordering. Parent containment is neither kind of edge.

Make one pure resolver, used by authoring/frontier, API packet and UI projections.
Ancestor applicability is explicit: `target_scope=subtree` reaches the target
and its descendants; `node` reaches only that node. A collapsed edge preserves
its true endpoints and is labelled partial when it targets only part of a group.
Validate cycles AFTER expansion, including a parent requirement on its own child.
Authoring must not publish a new typed hard cycle as an executable plan. Runtime
accepts observations and can display a legacy cyclic map with diagnostics.

Availability is not `node.status`: it is satisfied, missing, unknown, waived or
conflict, with requirement fingerprint, consumer workspace/basis and receipts.
`done` without the required output receipt is unknown. A verified output may be
available before the entire producer packet is finished. A stale receipt cannot
prove a new predicate. A waiver is an explicit explained decision, not evidence
that the output exists. None of these values grants permission or stops an agent.

When actual work precedes confirmed availability, show the actual activity and
an explainable dependency warning. Retain occurred_at and observed_at/receipt
sequence. Late evidence can resolve a current unknown; it cannot silently rewrite
the fact that the observer lacked that evidence earlier.

The old direct-only native /packet versus ancestor-aware authoring frontier is
a confirmed seam to repair. It does NOT establish the cause of the user's specific
incident: obtain exact IDs, plan version and event receipts if available, otherwise
return INCIDENT_NOT_RECONSTRUCTED while implementing the reproducible regression.

<a id="d5"></a>
## D5. Per-reader message filters
Reuse the old Symphony Observer's independent-reader semantics, not its agent
control functions. Categories: message, explanation, plan, command, tool, change,
test, agent, other. Preserve native_type. Error is an orthogonal flag. User/agent
role remains separate so a combined command/result item is not split into fake
executions. Native unavailable/encrypted reasoning is never reconstructed.

Apply category/error filtering in Store BEFORE the page limit. Absent filter
means All; explicit none means no types. OR selected categories; AND project,
node/edge/agent/deep and error facets. Deep streams deduplicate the same item
linked to several descendants. Filters never affect ingestion or retention.

Filter changes create a new query-bound cursor/window. Preserve one scroll/selection
state per query, not a global offset. New matching items update a visible count
without pulling a reader away from old text. Hidden categories cannot inflate
that count. An empty result distinguishes “nothing matching” from “nothing yet”
and “source disconnected”. Unknown native types remain under Other and All.

<a id="d6"></a>
## D6. Algorithm artefacts
An algorithm is a curated meaningful custom mechanism whose correctness/cost
warrants inspection: transformation, pagination/retry/deduplication, merge, graph
traversal, layout, scheduling or reconciliation. A library/framework choice,
trivial wrapper or one ordinary CRUD operation is not enough. Do not inventory
every function or force records in algorithm-free blocks.

Store one definition in the plan's algorithm dictionary; blocks reference IDs.
Badge opens the existing RIGHT inspector with direct algorithms, optionally
including descendants with provenance. The project Algorithms view reads the
same records. Distinct references deduplicate, and an algorithm can span blocks.

Definition includes purpose, inputs, outputs, steps, invariants, edge cases,
implementation references and testability. A planned implementation can be null.
References identify repo-relative path, symbol and exact revision; the plan does
not hold a second mutable source-code copy. Links/snippets are data, not commands;
no eval or arbitrary command/file read is introduced by the panel.

Observed correctness tests and benchmarks are event-ledger records linked to the
definition/implementation revision. Show implemented/tested/measured separately.
For an optimization retain old/new references, hypothesis, correctness evidence,
data/workload fingerprint, environment, method, units, n and actual measurements.
Only compare compatible cases; otherwise report NOT_COMPARABLE. Code/invariant
changes make affected evidence stale, not failed or implicitly current. No extra
model turn or benchmark after each edit; reuse ordinary tests and meaningful
before/after measurement when optimization is actually attempted.

Initial useful real Waypoint entries: plan three-way merge, effective prerequisite
resolution, item-target query/pagination and anchored message reconciliation.
Some are existing code, the resolver is new work. Do not invent measurements or
claim a definition's linked old test is valid for a changed implementation.

<a id="d7"></a>
## D7. Themes
Replace the binary toggle with an extensible registry. Keep Terracotta and Obsidian
and their exact references. A third intended style remains required but unidentified:
the accessible second and third selection files are byte-identical. Preserve three
selection slots, not three falsely completed themes. The registry can show a missing
reference notice, but must not present a duplicated Obsidian as the finished third.
Semantic test/error colors remain distinct from decorative red accent. N06 delivers
the registry and two retained themes; N09 delivers the actual third theme once its
reference is supplied. N08 can verify independent functionality but cannot certify
that all owner requirements are fulfilled while N09 is open.

<a id="d8"></a>
## D8. Backward compatibility and resource economy
Keep `waypoint.plan/1` envelope and existing node IDs. New semantics live in
`x_observability` profile 1. `/health` declares capabilities; old clients that only
retain fields do not gain semantics. Maintain old /items and packet fields while
adding explicit views. New clients must not pretend a legacy service supports
filters/prerequisite evidence. Local preferences never mutate plans.

This archive contains design, fixtures and contract models, not replacement runtime.
Use a current plan export, safe candidate merge and idempotent import. Retain old
history and event IDs. One shared-file integration owner; other parallel workers
write disjoint modules/contributions. Codex has a complete route for every node;
chat preparation never becomes a hard prerequisite. No schedule/claim is created
by opening the archive. Existing project resource policy MIXED remains unchanged.
