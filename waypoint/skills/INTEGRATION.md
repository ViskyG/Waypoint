# Skill publication / installation boundary

These two source candidates are part of this project design delivery. They are **not** installed in any Codex/chat session and have not been published to the canonical GitHub skill library.

The intended canonical locations, if the owner authorizes publication after target integration, are:
- `projects/waypoint/skills/shared/waypoint-map/SKILL.md` (+ faithful `SKILL.ru.md`)
- `projects/waypoint/skills/shared/waypoint-observe/SKILL.md` (+ faithful `SKILL.ru.md`)

Use the actual current `ViskyG/agent-skills/AGENTS.md` → skill-navigation → create-and-revise-skills route. Register each identity once in `catalog/projects.md`, regenerate the single navigator, update its Russian directory, run the library's navigation and validation tools, inspect the exact diff and read back the published revision. Candidate status must not be silently promoted to validated or installed. Do not change global resource policy, scheduler bindings or unrelated projects.

Existing roadmap creation should produce this **same** graph format, not an extra independently maintained plan. Existing task contracts can point at the map's stable IDs. Do not modify the global roadmap skill as an incidental installation side effect; provide the bounded integration change for review.

At local installation resolve the observer service and per-executor native identity. Read-only UI URL and write key are machine-local configuration, never literals embedded in SKILL.md. Pass only the selected short skill to the relevant executor. The runtime can work without either skill (passive capture and plan viewing); arbitrary block attribution still needs a verified sparse focus bridge.
