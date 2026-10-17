# Decisions and remaining doubts

## Chosen in this design
- Single local Python/FastAPI/SQLite service; plain JS/HTML/SVG passive UI, no build-time Node dependency in delivered runtime.
- Same normalized engine accepts proven VS Code private IPC plus persisted JSONL. No separate fallback product.
- Free declared status, observed activity, tests, and source health remain independent.
- Parent aggregated chat with direct-only toggle; off-map drawer; active retired nodes shown as ghosts. All reversible defaults.
- Focus is an explicit sparse semantic bridge, not a machine-guessed interpretation of raw prose.
- Plan snapshots are immutable; guarded updates and deterministic exports; no automatic write to user's Git repository.

## Scope-limited evidence, not new blockers
The owner's P09/P10/P11 prove live IPC access and historical genealogy on one extension version. The private protocol can change; the implementation must be checked against the current target. One latency sample is not an SLA. Full continuous live hierarchy, large-snapshot behavior, interruptions/rotation and the final rich UI still need target acceptance, not another competing architecture.

## Important missing operational capability in this design session
The currently exposed `files` connector provides list/search/read/find/materialize only. It does not expose `manage_library` or a guarded write. The existing global registry and inbox were read, but cannot be mutated through these actions. Preserve a local session/checkpoint and terminal publication request; do not claim the Library registry or Udot inbox was changed. Do not create a second queue. This is a delivery limitation, not permission to write Pro results into Drive contrary to the agreed workflow.

## Remaining decisions delegated to local integration
- Verify that native per-agent ID is actually distinct in the caller context; never inherit a parent's binding into descendants.
- Confirm the exact item container mapping for the installed IPC extension; schema and sample code were supplied but sanitized output omits message bodies.
- Tune frame/state and visible-node budgets from actual sessions. Defaults are protective, not product limits.
- Choose an exact dependency lock on the owner's Python environment after smoke tests; tested container versions are recorded separately.
- No licensing decision for public release has been made. Do not invent an open-source license or publish the private archive automatically.
