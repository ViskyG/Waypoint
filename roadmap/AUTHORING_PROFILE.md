# Waypoint roadmap authoring profile 1

This project profile is the binding between the existing `build-implementation-roadmap` skill and `waypoint.plan/1`. It is a deliverable of this planning pass, **not a newly installed global skill**. The existing skill chooses meaningful work and resource policy; this profile specifies the output shape.

## Minimum useful procedure

Read the accepted design, completed source handoff and actual available evidence. Preserve delivered work as source nodes; schedule only adaptation, missing implementation, integration and new evidence. Do not treat a stale design-session checkpoint as the latest release. Obtain the current source/base before revising an already active map.

Author one plan using the Waypoint schema bound to the accepted source package, even if the viewer is not yet installed or running. Every meaningful node has a stable ID, title, explicit parent, sufficient assignment, observable acceptance conditions, relevant named tests, layout hints and precise source references. Put global provenance/policy and per-node execution context under `x_roadmap` so the existing importer preserves them. The mandatory instructions must remain visible through the actual native packet response; do not rely only on extension fields the packet route does not return.

Use the accepted design's capsule identities. Nested stages refine the same work; they must not create duplicate parent-and-child implementation assignments. Record direct dependencies once as graph edges. Define file/anchor ownership for parallel packets and an integration owner for shared contracts. A `preferred_executor` is never a claim or spend authorization.

Generate the human roadmap, local packet context and Runner grouping from that same plan. Keep the source JSON, not generated Markdown, as the authoring input. Preview is an optional read-only snapshot. Files absent from the allowed source are explicit gaps or proposed new files, not fictitious existing implementation.

Validate with the actual Waypoint schema and domain validator, then one disposable import/read/export/packet round-trip. Check extension preservation, reference integrity, stable IDs and deterministic views. A fixture import proves interchange, not live Codex integration. Reuse relevant prior evidence rather than repeat unrelated checks.

When updating, export the current head, preserve unchanged IDs and base_version, and produce one bounded snapshot/change package. No timestamp-wins or forced overwrite of another agent's plan. Immutable event history is not part of the editable plan. Send sparse lifecycle signals only through the existing verified binding; do not ask agents to summarize conversations for the UI.

## Reuse and limits

`templates/PROJECT.plan.json` demonstrates the same schema with another project ID. It is intentionally marked TEMPLATE and UNSELECTED resource policy. Replace its requirements, tests, sources and ownership before using it; it is not a second project scheduled by this archive.

This profile applies to the **format of future maps**, not mandatory use of every Waypoint feature in every tiny project. One compact map is sufficient for a small task. Do not introduce a new workflow service, separate queue or parallel task graph.

## Условие результата

Карта, подготовленная в чате, загружается в Waypoint без повторного проектирования и ручного перевода; задания и человекочитаемые представления получаются из неё же. При изменениях источника/версии повторно проверяется только затронутая совместимость. Публикация этого профиля в общих скилах — отдельное явно согласованное изменение, а не побочный эффект импорта карты.
