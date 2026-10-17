# Publication receipt and exact remaining transfer

**Current status: NOT_WRITTEN_TOOL_UNAVAILABLE.** The package and progressive checkpoints are available as files in this conversation. The canonical Library coordination files were read; they were not modified.

The current Files connector exposes list, search, read, find and materialize. Capability discovery also queried write/manage_library, but returned no callable create/update/guarded-write action. Thus no registry write call could be issued. This is absence of a capability, not a provider permission denial and not a successful queued notification. Pro did not bypass its read-only Drive role.

## Existing targets, do not create replacements

- `/WorkBelt/handoff/CAPSULE_REGISTRY.json`
- `/WorkBelt/handoff/DOT_RESULTS_INBOX.json`

Their contents were inspected in this pass. Other projects and even another project's ACTIVE design session exist. They are unrelated and must remain untouched. Previously observed backing file IDs/revision numbers are not durable bindings and are deliberately not embedded in these requests.

`REGISTRY_MERGE_REQUEST.json` contains only the proposed Waypoint project/session/capsule upserts. `UDOT_TRANSIT_ITEM.json` contains one proposed design-result notification. They are transfer requests, **not another registry, inbox, scheduler or executable task queue**.

## Procedure for an authorized Library writer

1. Publish this final package and the terminal handoff using the existing project/transit storage workflow. Obtain actual readable artifact references. Do not turn a sandbox path or a filename into an invented Library URL.
2. Re-resolve the existing targets by canonical path and obtain stable Library identities plus their **current** content versions. Read each entire file. Inspect any current Waypoint records; a different active owner or incompatible existing record is a conflict requiring reconciliation, not blind replacement.
3. Bind each `{archive_ref: null, member: ...}` in the proposed records to the actual published archive reference. Preserve the member path so an executor can open the assignment directly. Set the project's artifact root to a real published location. Do not publish unresolved `null` references as runnable assignments.
4. Merge only Waypoint's project/session and the seven named capsule records into the current registry. Preserve all unrelated records and fields. Increase registry revision only according to that actual schema. Write with the provider's fresh conditional-write/version guard. On conflict, read the newest complete content and merge again; never reuse stale whole-file contents.
5. The design session is terminal `COMPLETED`. C01–C04 mean source artifacts produced, not target validation. C05–C07 are the remaining work contracts, with their dependencies. Mark nothing installed or integrated merely because the archive is copied.
6. Verify the registry readback, including unrelated-record preservation, terminal session and resolved assignment references. Then merge the single inbox item idempotently by its stable notification ID. Do not mark it ACCEPTED or add it to a consumer's `seen` list yourself. Perform a separately guarded inbox write and readback.
7. Report exact published references, resulting registry/inbox versions and remaining target integration. Publication of a design-result record is not permission to launch arbitrary jobs, contacts or model/API spending.

If a write tool is still unavailable, keep these requests and return the package directly to the user. Do not make a second queue or claim Udot received it. The user can independently hand `CODEX_START.md` and this archive to local Codex without waiting for automated transit.
