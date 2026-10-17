# Additive observability API, version 0.2

The unchanged `waypoint.plan/1` envelope accepts `x_observability` profile 1.
Generated schemas live in `schemas/`; exact source contracts are in
`../next-stage/design/CONTRACTS.md`. Unknown extensions and legacy unclassified
edges are preserved. The existing read/write capability boundary remains in force.

`GET /api/health` advertises installed capabilities. `GET /api/projects`
retains its original shape; `?summary=true` returns metadata and distinct active
agent/leaf counts without reading transcript bodies. Missing source knowledge is
explicit. State includes shared `node_views` and a basis containing plan version,
event cursor and projection version. Map, Plan, packet and frontier share effective
dependency semantics. Free status strings never prove availability.

`GET /api/p/{project}/prerequisites?node=ID&phase=start|finish&workspace=REF`
returns effective requirements with inherited true endpoints and matching immutable
evidence. Consumer/project workspace bases are explicit authored references.
Conflicting current reporters, stale revisions and absent evidence remain visible.
Early-work warnings retain the evidence available at their receipt boundary.

`GET /api/p/{project}/items` adds `categories` (CSV), `only_errors`, `outside`, and
`page_cursor`. Absent categories means all; `none` or empty CSV means no categories.
Unknown categories return 422. Categories OR together, with explicit machine error
metadata ANDed. Text is never searched to infer failure. Facets/targets filter
identities before limit/body loading. Opaque older-page cursors bind project,
resolved plan, scope, actor, depth and filters; they are not authentication. Mixing
`before` with `page_cursor`, or reusing a cursor with another query, returns 422.
The event cursor remains separate. Ordering is total over first receipt, actor, ID.

`GET /api/p/{project}/algorithms?node=ID&deep=true&version=VERSION` and
`GET /api/p/{project}/algorithms/{ID}?before=SEQ&limit=100&version=VERSION`
show saved definitions and revision-aware evidence. Code/test paths are displayed
as data, never executed or read through a browser endpoint. Correctness,
measurement and integration receipts are separate. Measurements compare only with
matching recorded conditions and confirmed correctness; no global speed claim is
inferred. Observations use `algorithm.observation` and `dependency.observation`;
source time and receipt time are distinct. No endpoint controls an agent.
