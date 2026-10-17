# Waypoint roadmap authoring profile 1

This project profile is the binding between the existing `build-implementation-roadmap` skill and `waypoint.plan/1`. It is a deliverable of this planning pass, **not a newly installed global skill**. The existing skill chooses meaningful work and resource policy; this profile specifies the output shape.

All three roles—roadmap designer, executor and auditor—also follow the project
[workflow contract](../next-stage/skills/conformance/WAYPOINT_WORKFLOW.md).
It specifies scenario evidence, immutable proof, each executor's own binding and
scope, criterion registration before completion, scope release and bounded fixes.
The latest [conformance audit](../next-stage/audit/CONFORMANCE_RU.md) records the
current acceptance limits; historical green counts are not a full product verdict.

## Minimum useful procedure

Read the accepted design, completed source handoff and actual available evidence. Preserve delivered work as source nodes; schedule only adaptation, missing implementation, integration and new evidence. Do not treat a stale design-session checkpoint as the latest release. Obtain the current source/base before revising an already active map.

Author one plan using the Waypoint schema bound to the accepted source package, even if the viewer is not yet installed or running. Every meaningful node has a stable ID, title, explicit parent, sufficient assignment, observable acceptance conditions, relevant named tests, layout hints and precise source references. Put global provenance/policy and per-node execution context under `x_roadmap` so the existing importer preserves them. The mandatory instructions must remain visible through the actual native packet response; do not rely only on extension fields the packet route does not return.

Use the accepted design's capsule identities. Nested stages refine the same work; they must not create duplicate parent-and-child implementation assignments. Record direct dependencies once as graph edges. Define file/anchor ownership for parallel packets and an integration owner for shared contracts. A `preferred_executor` is never a claim or spend authorization.

Generate the human roadmap, local packet context and Runner grouping from that same plan. Keep the source JSON, not generated Markdown, as the authoring input. Preview is an optional read-only snapshot. Files absent from the allowed source are explicit gaps or proposed new files, not fictitious existing implementation.

Validate with the actual Waypoint schema and domain validator, then one disposable import/read/export/packet round-trip. Check extension preservation, reference integrity, stable IDs and deterministic views. A fixture import proves interchange, not live Codex integration. Reuse relevant prior evidence rather than repeat unrelated checks.

When updating, export the current head, preserve unchanged IDs and base_version, and produce one bounded snapshot/change package. No timestamp-wins or forced overwrite of another agent's plan. Immutable event history is not part of the editable plan. Send sparse lifecycle signals only through the existing verified binding; do not ask agents to summarize conversations for the UI.

## Reuse and limits

`PROJECT.plan.json` demonstrates the same schema with another project ID. It is intentionally marked TEMPLATE and UNSELECTED resource policy. Replace its requirements, tests, sources and ownership before using it; it is not a second project scheduled by this archive.

This profile applies to the **format of future maps**, not mandatory use of every Waypoint feature in every tiny project. One compact map is sufficient for a small task. Do not introduce a new workflow service, separate queue or parallel task graph.

## Условие результата

Карта, подготовленная в чате, загружается в Waypoint без повторного проектирования и ручного перевода; задания и человекочитаемые представления получаются из неё же. При изменениях источника/версии повторно проверяется только затронутая совместимость. Публикация этого профиля в общих скилах — отдельное явно согласованное изменение, а не побочный эффект импорта карты.

## Observability profile 1

When `observability_profile_1` is available, author project purpose and one
`x_observability.intent` per meaningful node: `summary`, `context`, `change`,
optional `scope`. This is the owner’s explanation, separate from `assignment`.
Keep unknown extensions, IDs and layouts on revision. Missing legacy intent is
explicitly incomplete data, not a request for a model-generated runtime summary.

A `requires` edge names a producer output and matching positive revision, phase
(`start`/`finish`), explicit target scope (`node`/`subtree`), workspace policy and
reason. `order` expresses preferred sequence without an output condition. Keep
legacy unclassified arrows visible rather than automatically making them hard
requirements. Use the installed shared dependency resolver for Plan, packet and
frontier; free `done` status never proves that an output is available. Record
actual availability through dependency observations, preserving unknown/conflict.

Curate only meaningful custom algorithms in the project dictionary. Nodes reference
stable IDs, including shared algorithms. Definition, exact code revision, authored
tests, executed correctness, measurements and installed integration are separate.
No benchmark tables or copied implementation live in the plan. Runtime observations
are immutable ledger records. Use compatible workloads, data, units, methods and
correctness before making any improvement claim; keep stale evidence historical.

Generate Plan, Task and executor views from this one graph, joined to runtime
status rather than manually maintained status documents. Chat capsules remain
optional supply, and each task retains a permitted non-chat route. The template
uses another project ID and UNSELECTED policy; it conveys no resource permission.

Prepare migrations from a fresh installed export plus base version and stable
request ID. Review a bounded candidate before import. The helper
`next-stage/tools/prepare_authoring_revision.py` is deliberately specific to the
Waypoint legacy map; another project starts from the transferable template. New
instructions activate only after their actual capability is advertised.
