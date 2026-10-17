# Source assessment — 17 October 2026

## Current implementation, not the earlier source-only ZIP
Inspected `ViskyG/Waypoint` at commit `c36e2e9a296ec8a78e4a19fad1975ea6ed951ade`. Its `waypoint/reports/RETURN_TO_CHAT_RU.md` reports completion of R00/C05/C06/C07 and records local live tests. This design does not independently certify that installation. New changes must be applied on the actual current workspace, not by overwriting it with the October 16 archive. No local execution log explaining the owner's particular out-of-order observation was supplied.

Relevant inspected sources (paths relative to repository):
- `waypoint/waypoint/server.py` blob `91790ca3430c9b97e94fb76b3e9f43ee747cf3e2`: `/api/projects` already exists. `/packet/{node}` returns ONLY direct predecessors, assignment, acceptance, tests, source_refs, children. The `/items` route has node/edge/agent/deep/before/limit/version, but no type filter.
- `waypoint/waypoint/store.py` blob `47d85868ad07fafac984e569133330599c28d204`: native project keys and many-project heads already exist; item paging uses target associations and first_seq. Node status projection writes directly addressed nodes, not parent status. `/state` returns the plan plus current event projections; a selected historical plan is NOT a historical runtime-state replay.
- `waypoint/waypoint/web/app.js` blob `504c0b0f47f4c87520163a651dac8645a107c926`: two-way theme toggle, existing project dropdown, assignment text directly displayed, per-reader project/version/deep identity, keyed DOM and selection/scroll preservation already implemented. There is no catalogue page, typed-message filter, human-intent subtab or algorithm drawer.
- `waypoint/waypoint/domain.py` blob `80b26ecb4d87933ac031c7c75d4c16522fbd71fc`: `waypoint.plan/1`, extension fields preserved, raw dependency cycles produce warnings; parent cycles rejected. Free status intentionally remains free text.
- `roadmap/tools/roadmap.py`: offline `frontier(..., stages=True)` considers ancestor predecessor edges. `/packet` does not. Do NOT replace this with a second third implementation of prerequisite semantics: one shared pure resolver should serve all views.

## What the order observation can and cannot establish
Confirmed mismatch: the native packet for a nested stage can omit a parent's prerequisite. Example in delivered map: C05.1 has no direct predecessor, although C05's R00 prerequisite applies to its stages in the authoring tool. It is a concrete implementation seam, NOT proof that it caused the owner's exact observed execution.
Other distinct cases to diagnose: a collapsed C05→C06 arrow represents C05.3→C06.3 rather than all of C05 blocking all of C06; a child can be active while its parent's separately reported status remains waiting; late/missing telemetry can hide earlier work. Record the actual node IDs, plan version, source sequence/receipt and missing prerequisite before calling an incident an execution violation.

## Old Observer behaviour
Inspected `ViskyG/SymphonyObserver/README.md`, sections Interface / Current additional installation, and Library `/Symphony Observer/2026-10-13/symphony-observer-checkpoint-04.zip`, `src/symphony_observer/static/app.js`.
Actual dropdown choices in that older source: all, reasoning, message, command, diff, control, error, protocol. Labels also exist for plan, tool, subagent, lifecycle, system, user and reasoning_text. Command/result is combined in that UI. The new Waypoint filter should preserve the independent-reader behaviour, NOT import the old Observer's stop/approval/control abilities. Proposed extra filter facets are proposals, not a claim that all were old dropdown choices.

## Theme evidence and open reference
The three selected attachments are present. SHA-256:
- `image(20261016-145245).png`: `794ca5d7e23bf3bddeb6f1ae6d39bb70dbe6964be365196caf3a1d10e70b8588`.
- `image(20261016-145251).png`: `087db550daab26e5be7404bef2e74b86e1b9aa3cc266cdb022172375bdd773a4`.
- `image(20261016-145253).png`: `087db550daab26e5be7404bef2e74b86e1b9aa3cc266cdb022172375bdd773a4`.
The second and third accessible files contain identical bytes. This limits recovery of the intended THIRD DISTINCT appearance. It does NOT authorize reducing the owner's requirement to two styles. Three selection slots remain; the third requires the intended image/name before pixel-level acceptance. Do not invent a dark theme or duplicate Obsidian and claim completion.

## Source pointers
https://github.com/ViskyG/Waypoint/tree/c36e2e9a296ec8a78e4a19fad1975ea6ed951ade
https://github.com/ViskyG/SymphonyObserver/blob/main/README.md
https://github.com/ViskyG/agent-skills/blob/e42beeb26a1065ec57af2999f2970046ccd21f53/skills/chatgpt/build-implementation-roadmap/SKILL.md
Original runtime ZIP in this chat was inspected for the prior graph and pure planner, not used as a replacement current codebase.
