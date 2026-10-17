# Exact next-stage contracts

Status: designed target contract. These additions are NOT yet implemented in the
inspected service. The packet assignments identify who implements each seam.
All paths below are relative to the Waypoint repository, not this archive.

<a id="c1"></a>
## C1. Profile and readable intent
Keep `schema=waypoint.plan/1`, existing fields and unknown extension keys.
Plan `x_observability`:
```
{schema: "waypoint.observability/1", purpose: string,
 algorithms: {algorithm_id: AlgorithmDefinition}}
```
Node `x_observability`:
```
{intent: {summary: string, context: string, change: string, scope?: string},
 outputs: {output_id: {definition: string, revision: integer >= 1}},
 algorithm_refs: [algorithm_id]}
```
Intent fields are plain text/escaped Markdown; summary is not a separate task.
`assignment` retains its original executor meaning. No status/test-run fields
are inserted into intent. Empty intent is explicitly legacy/incomplete. Unknown
extensions survive round-trip; missing definitions are warnings for legacy data,
errors for newly authored profile claims.

<a id="c2"></a>
## C2. Typed relation
Edge keeps `from`, `to`, ID. Its `x_observability` is:
```
{relation: "requires" | "order", phase: "start" | "finish",
 target_scope: "node" | "subtree", why: string,
 condition: {output_id: string, revision: integer,
             workspace: "consumer" | "project"}}
```
`condition` is mandatory for requires and absent for order. It refers to an
output of `from`; revision must match that output definition. All effective hard
conditions are conjunctive (AND). Alternatives require a new explicit design,
not implicit OR guessed from several edges. A missing extension on a legacy edge
retains the visible link but yields unclassified/unknown availability.

`effective_requirements(plan, node_id, phase)` returns sorted records:
```
{edge_id, producer_id, declared_target_id, consumer_id, phase, inherited,
 output_id, condition_revision, requirement_fingerprint, why}
```
Include direct target edges. For ancestor targets include only target_scope=subtree.
Do not inherit merely because IDs contain dots. Ignore order for readiness, keep
it in the view. Expansion tests self-dependencies/cycles on requires edges;
start and finish availability are separate queries. No need to complete a parent
before entering its own children. An explicit parent-subtree contract applies to
all consumers and must not be fabricated for style/layout reasons.

Fingerprint is SHA-256 of canonical JSON containing source/target IDs, consumer,
phase/scope, output_id, revision, normalized output definition, workspace policy.
Normalize whitespace, not meaning. Exclude layout, theme, why and intent. Changing
an output's meaning increments revision; changed definition also invalidates even
if an author forgot the increment. Cosmetic positioning must not invalidate.

<a id="c3"></a>
## C3. Evidence and discrepancy projection
New event kind `dependency.observation`, through existing authenticated ingest:
```
payload = {edge_id, consumer_id, requirement_fingerprint,
 workspace_ref, availability: "available" | "missing" | "waived",
 basis: {kind: "artifact"|"test"|"executor_attestation"|"waiver",
         ref: string, revision?: string, explanation: string},
 occurred_at: ISO8601}
```
Envelope still has event_id/project_id/source/at, node_ids and optional agent_id.
`at` is when the reporter observed it; Store receipt seq is the ingestion order.
Caller stamps once for retries. Optional `supersedes:[event_id]` explicitly reconciles prior observations. Within one reporter, the latest durable observation replaces that reporter’s own statement; contradictory current reporters remain conflict, not timestamp-wins. These records assert facts with provenance; no
arbitrary executable predicate in the payload. View evaluation is not a policy
engine. Accept actual node/status/activity independently of readiness.

Evaluate only matching fingerprint AND applicable consumer workspace. Latest
consistent observation supplies satisfied/missing/waived. No matching observation
is unknown; contradictory simultaneously applicable evidence is conflict until
explicit reconciliation. Preserve stale receipts in history with stale reason.
Waiver requires explanation and author identity. Free `status='done'` NEVER creates
availability. Consumer-base changes require checking workspace-dependent evidence.

`started_without_confirmed_prerequisite` is a read warning tied to scope/start
observation and snapshot/cursor. Distinguish unknown from explicitly missing.
Use source occurred_at and receipt order to report lateness, not total ordering
across unrelated processes. If past graph/workspace data are absent, diagnosis is
inconclusive; do not rewrite an old claim into certain execution misconduct.

<a id="c4"></a>
## C4. API additions and a single projection
Existing APIs remain valid. Declare added features in `/api/health.capabilities`:
`observability_profile_1`, `effective_dependencies_1`, `typed_items_1`,
`project_summary_1`, `algorithm_evidence_1`. A capability is advertised only when
its implementation/contract checks are installed, not by a static future list.

- `GET /api/projects?summary=true`: existing project_id/title/version plus purpose,
  distinct_active_agents, distinct_active_blocks, last_observed_at, source_health.
  No bodies/messages. Unknown health/count distinguished from zero. Existing
  no-query response remains compatible.
- `GET /api/p/{project}/state`: same core response, plus observability read fields
  joined under one `{plan_version, cursor, projection_version}` basis. Both Map and
  Plan receive the same node_views keyed by ID; they do not re-evaluate separately.
- `GET /api/p/{project}/packet/{id}`: keep assignment, acceptance, tests, source_refs,
  predecessors and children. Add intent, prerequisites.start/finish and
  dependency_warnings, algorithm_refs, basis. `predecessors` stays legacy direct
  list; new agents use prerequisites when the capability is present.
- Optional `GET .../prerequisites?node=...&phase=start&workspace=...`: delegates to
  that SAME resolver/evaluator, no copied algorithm.
- `GET .../algorithms?node=...&deep=false&version=...`: definitions plus revision-aware
  evidence summaries, unique IDs, direct/inherited association source.
- `GET .../algorithms/{id}?version=...`: one definition, implementation refs and
  paged evidence. Never executes code/test commands from a record.

New reads use the existing token/origin/host boundary. No provider control routes.
No unauthenticated catalogue or arbitrary local source-file endpoint. Repository
links escape names and allow http(s) or displayed local references only. Optional
code snippets must come from an explicitly allowlisted checkout/revision and are
escaped, read-only and labelled; links alone are an acceptable first implementation.

<a id="c5"></a>
## C5. Typed message paging and live readers
`GET .../items` adds optional categories (comma-separated), only_errors (boolean),
page_cursor (opaque). Existing before/limit reads work unchanged when page_cursor
is absent. Reject simultaneous before+page_cursor. Absent categories means All;
`categories=none` means empty selection. Categories listed in D5; unsupported
category returns 422, unknown native kinds map to other. Roles and native types
are preserved, not inferred from prose. only_errors requires explicit failure
metadata; a red theme or text mentioning “error” is not evidence of failure.

A normalized item has one primary category and an is_error flag. A command/result
compound remains one native identity. Add a bounded classifier mapping actual
provider types to categories. Explicit test or plan events qualify; arbitrary
command stdout is not parsed by an LLM into assumed test success.

Query order: project + associations + agent + deep membership + type/error facets
→ deduplicate native item identity → stable total key `(first_seq, agent_id, id)`
→ page restriction → body fetch. Never take newest 500 and then filter. Maintain
indexed projections in the same transaction as item.upsert/identity_corrected/link;
rebuild from ledger must reproduce them. Add indexes only after EXPLAIN/fixture
shows the intended indexed predicate, not a magical performance assertion.

Opaque page cursor encodes version, direction, boundary key, resolved plan version
and query hash including project/scope/agent/deep/categories/errors. Validate type,
length, query binding, version and bounds. Cursor is NOT authentication. Malformed
or mismatched cursor yields 422 `cursor_scope_mismatch`; client starts a new window.
Pagination is a LIVE view, not MVCC time travel. Item corrections may remove/add
matches; refresh affected readers from events and retain provenance. Do not claim
snapshot isolation merely because the cursor has a plan version.

Existing event cursor is a DIFFERENT thing: it is the last observed project ledger
seq. Do not overload a paging cursor with stream acknowledgements. Event delivery
still runs unfiltered; client uses changed identities/category to invalidate all
affected reader windows, including an item that changed FROM a visible category.

Reader identity: service/project/resolved-plan/channel/node-or-agent/deep/filter.
Use AbortController/request-generation and restore anchor item + pixel offset,
not only scrollTop. New matching count counts unique visible new identities only.
Selection/old-message reading preserved. Global default preference seeds new
readers; changing one reader does not mutate the plan or another reader.

<a id="c6"></a>
## C6. Algorithm definition and observations
AlgorithmDefinition:
```
{id, title, purpose, inputs: [string], outputs: [string], steps: [string],
 invariants: [string], edge_cases: [string], definition_revision: integer,
 implementation: null | {repository, revision, refs:[{path,symbol}]},
 testability: {strategy, test_refs:[{path,symbol?}], missing_cases:[string]},
 resource_risks:[string]}
```
Keys/refs bounded and project-scoped. Keep definition in plan; observations below
are immutable event records. No benchmark table in a continuously mutated plan.

New `algorithm.observation` payload:
```
{algorithm_id, definition_revision, implementation_ref, observation_kind,
 correctness:{outcome:"passed"|"failed"|"not_run", evidence_refs:[...]},
 measurement:null | {metric, unit, n, value, statistic, method, environment_ref,
                     dataset_ref, workload_ref, semantic_revision, direction:"lower"|"higher"},
 comparison:null | {baseline_observation_id, candidate_observation_id,
                    constraints, claim}, note}
```
Require real evidence refs for passed/failed; mark authored-only tests not_run.
Missing measurement is NOT zero. Values finite; n>0; units explicit. Compare only
matching metric/unit/method/dataset/workload/compatible environment and semantics,
with recorded correctness. Show NOT_COMPARABLE with reasons otherwise; show a
regression, not selective speedup, if memory/I/O/correctness constraints degrade.
Definition or implementation revision mismatch labels stale. Target integration
receipt is needed before “installed” is shown; code link alone is “implemented”.

<a id="c7"></a>
## C7. Authoring and merge delivery
The stage map in this archive is a stage fragment with `project_id=waypoint` and
new WPT-N* IDs. `tools/prepare_stage_merge.py` prepares a whole proposed plan from
a current export while preserving old nodes/edges and extensions. It never writes
the service or infers the current head from this package. New evidence starts empty.
Keep request_id stable for byte-identical retry; get fresh base on conflicts.

A complete profile schema and reference model fixtures are supplied for validation.
They are implementation oracles, not an installed API. N01 adds runtime capability,
N02 adopts the shared dependency resolver, N07 updates authoring to emit this
contract, and N08 checks all consumers agree. Native acceptance of JSON extensions
alone is insufficient evidence of these behaviours.
