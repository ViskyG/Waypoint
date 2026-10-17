---
name: waypoint-observe
description: "Use Waypoint's sparse local work signals during authorized agent work, without summaries, polling turns or changing execution authority."
metadata:
  version: "0.2.0"
  status: "draft-candidate"
---

# Observe work without making work for the observer

Use the current project and **distinct native agent identity**, obtained from the validated executor binding. Codex `payload.id` is distinct; a shared `session_id` or inherited parent's binding is not. If binding is unknown, leave the observed transcript unassigned and resolve the identity once through the installed integration. Do not invent an ID or attribute child work to its parent.

At a change of working scope, emit one command:

```bash
wp --project PROJECT --agent codex/NATIVE_ID focus W-02 W-03
```

Use empty focus to release a scope. Several blocks or an off-map reference are valid; there is no exclusive reservation. Native messages/tools are captured automatically. Do not summarize them for Waypoint, repeatedly report heartbeat, query the model for status or reload the whole map. Use `wp --project PROJECT packet W-02` when the task actually needs its compact contract.

At meaningful status/check/result boundaries use `status`, `test` or `done`; these commands describe observations, not permission to proceed. Combine signals with the ordinary work command where useful. Test results must state the actual run/outcome and basis; absence of a run is not green. Done may coexist with failed tests when the executor explicitly explains that outcome. Include expected/actual differences in `done --result TEXT --diff TEXT`; do not silently rewrite the acceptance criteria.

`QUEUED_LOCALLY` means recorded in the local outbox, not delivered to the viewer. A telemetry failure does not stop the real task; preserve the missed signal once and continue authorized work. Invalid plan edits or conflicting operation IDs are different: do not claim they were applied. Do not retry in a tight inference loop.

The observer never sends start/resume/steer/approval/stop to agents. Installation, native binding and source adapter repair are separate bounded integration work. This candidate is not installed or globally registered.

## Joined views and revision-aware evidence
Do not populate the viewer's Plan or project summaries separately: they derive
from the existing node/event record. Reader filters are local viewing preferences;
never stop collecting messages because a category is hidden. Use the feature's
actual capability/contract before relying on new typed queries or prerequisites.

For a meaningful prerequisite/output or algorithm change, attach existing artifact,
correctness or measurement receipts with source and applicable revision/workspace.
Do not convert arbitrary status text into proof, invent success, or rerun tests
solely to fill a panel. If work proceeds with unknown prerequisites, preserve the
activity and explained discrepancy; no provider-control RPC is introduced. An
old measurement tied to other code stays historical/stale, not a fresh speedup.
