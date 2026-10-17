# Implementation boundaries, migration and integration

<a id="i1"></a>
## I1. Directory conventions
Repository layout is `roadmap/` and `waypoint/`; the Python package is
`waypoint/waypoint/`. Do not mistake the archive directory for that runtime.
Current frontend is `waypoint/waypoint/web/app.js` (IIFE), index.html and style.css.
Current source files named below exist at the inspected commit; new module names
are explicit design choices, not claims that they already exist.

<a id="i2"></a>
## I2. Responsibilities and seams
- Existing `domain.py`: preserve pure native validation and merge. Extend via a
  small `observability.py` module for profile/algorithm validation and defaults;
  do not stuff provider/network code into the domain.
- New `dependencies.py`: one pure effective-requirement resolver/fingerprints and
  availability evaluator. `roadmap/tools/roadmap.py`, packet and read projection
  call it; browser consumes results, not a reimplementation.
- New `read_models.py`: bounded catalogue and node/plan/algorithm projections.
  Shared status/activity semantics for Map and Plan. No separate mutable statuses.
- Existing `store.py`: single DB owner, migration and event projection, indexed
  filtering, evidence projection and item identity correction. Keep lock/transaction
  semantics. Introduce cohesive helper module if needed, not one class/file by fiat.
- Existing `server.py`: compatible query parameters and routes invoking same
  services. Keep host/origin/read-write token boundary. Do not duplicate logic.
- Existing CLI: compact packet already points to execution assignment. Add effective
  requirements/capability display without sending the full plan on every command.
- UI: add small cohesive modules `web/projects.js`, `web/plan.js`,
  `web/algorithm_panel.js`, `web/filters.js`, `web/themes.js` plus shared view model.
  The existing app.js remains source/event/navigation orchestrator. Migrate loading
  once to same-origin ES modules (no build chain) OR bind equivalent explicit
  module interfaces; the choice must preserve CSP, offline preview and tests.

UI module contract (role-level, signatures fixed for integration):
```
mountProjectCatalogue(container, summaries, {onOpenProject}) -> dispose
mountPlan(container, view, {onOpenNode, preferences}) -> {update(view), dispose}
mountAlgorithms(container, view, {onOpenAlgorithm, onOpenNode}) -> {update, dispose}
bindTypeFilter(container, query, {onChange}) -> {update, dispose}
getThemeRegistry() -> [{id,label,reference,state}]
```
All user/provider strings escaped. UI callbacks change viewer state or request
read APIs, never invoke provider execution. `view.basis` guards old-project replies.

<a id="i3"></a>
## I3. Changes per packet and ownership
N01 owns native/profile validator integration and initial DB migration scaffolding.
N02 owns dependencies.py, packet/frontier integration and prerequisite evidence.
N03 owns catalogue/Plan/Task UI shell and common navigation/view model.
N04 owns typed query projection and reader filters.
N05 owns algorithm projection/UI and revision-aware evaluation.
N06 owns theme registry/tokens; preserves references.
N07 owns authoring/templates and bounded skill candidates.
N08 is final integration owner for all shared files and target rollout.

Default is sequential shared-file integration. Parallel contributions MUST name
owned new modules and exact edits to shared files. They cannot both replace
store.py/app.js/browser tests. A waiting integration edit is an ownership conflict,
not a fake graph dependency. Tests that share a mutable fixture DB run isolated.

<a id="i4"></a>
## I4. Database plan
Inspected code already migrated runtime schema 1→2 for item_targets. N00 discovers
actual schema/head; NEVER assume the same version on a newer checkout. Next migration
adds item category/error projection and dependency/algorithm observation indexes.
Use existing accepted events as authoritative history; projections are disposable.
If ALTER is inconvenient, auxiliary tables keyed by project/agent/item are allowed,
but no second event store. Index associations/type before loading full message text.

Backup with the existing safe SQLite backup mechanism before migration. Migration
is one idempotent transaction; populate category projections from stored native
items and initialize evidence indexes without inventing passed results. Data beyond
the known schema is preserved or explicitly blocks only migration. Check interrupted
transaction rollback, reopened DB and rebuild. Backfill categories deterministically
without model calls. Legacy unknown payloads remain queryable under Other.

<a id="i5"></a>
## I5. Plan migration
Read a fresh installed plan export. Prepare a new revision with intent/outputs/
algorithm refs and typed edges. Preserve every existing ID, assignment, test, source
ref, unknown extension, history and runtime status. Only rewrite descriptions once
as authoring work. Require meaningful before/after context, not automatic truncation.
Do not auto-convert every old arrow to a hard edge: review actual input requirement.
Unclassified legacy edges remain visible with unknown prerequisite semantics.
Preserve old layouts. Publish independent new stage branch beside old completed work.

Plan changes use current base_version + stable request_id; same response-unknown
retry resends identical bytes. A conflict is not timestamp-wins. Display old plan
snapshots with explicitly CURRENT runtime observations unless historical replay
has actually been implemented. Do not insert completed test events from fixtures.

<a id="i6"></a>
## I6. Rollout and rollback
Stage on a disposable copy and same-origin test service first. Before applying to
the selected installed Waypoint, snapshot its code/dependency bindings and DB.
Do not stop or resume Codex. Brief Waypoint maintenance/reconnect can be required;
communicate the affected observer service and preserve its delivery spool.

A failed plan import is atomic. A failed DB migration rolls back; rerun after repair
against the same inputs. For app rollback preserve all accepted events since backup:
prefer forward-compatible previous code + old plan version, or drain/export/replay
new events into the restored copy. NEVER restore an old DB over new accepted data
and call it lossless. Existing old code ignores unknown event kinds, but verify
that property on actual target. Old UI may display old plan fields only: say degraded,
not full support. New source collectors do not change in this stage unless a
reproducible defect in affected mapping is found.

<a id="i7"></a>
## I7. Performance and evidence economy
The performance concern is duplicate scans and uncontrolled payload/DOM growth,
not a speculative target FPS. Record representative 100/300 rich-block datasets,
some 500-message hot blocks, selected filters and concurrent project switch. Measure
n/method/environment explicitly. Verify bounded visible windows and indexed selection;
do not promise a latency from the old n=1 IPC measurement. Repeat only invalidated
checks after contract/index/UI changes. The delivered model tests do NOT establish
runtime/browser performance, live Codex correctness or third-theme acceptance.
