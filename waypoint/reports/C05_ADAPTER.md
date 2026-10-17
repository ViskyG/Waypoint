# WPT-C05 adapter completion evidence

Implemented in the supplied existing adapter and collector; no second observer or agent execution channel was introduced.

Changed paths: `waypoint/adapters/codex.py`, `waypoint/adapters/patches.py`, `waypoint/adapters/ipc.py`, `waypoint/collector.py`, `tests/test_adapter_incremental.py`.

- Indexed known history roots and native item paths. A normal item text patch normalizes only that item. Array insertion/removal rebuilds its containing subtree; unknown history structure rebuilds the affected known root and emits a diagnostic. Settings, instructions, tool argument trees and encrypted reasoning are excluded from item discovery.
- Recent source revision cache is bounded at 256 entries. Exact repeats do nothing, conflicting changes at a cached revision are diagnosed separately from gaps, and authoritative hydration repairs invalid state. Older revisions outside the cache are stale observations, not a consistency proof.
- Collector coalesces intermediate revisions for 200 ms by default (`WP_COALESCE_MS`, supported range 0–5000 ms); terminal item and idle activity changes flush immediately. It preserves exact provider text of the emitted revision.
- Source cursor contains `source_key=ipc:<project>:<native-thread>`, `project_id`, `native_id`, `generation`, `revision`, `received_revision`, `hydrating`. Item evidence carries `source_key`, `source_generation`, `source_revision`, `source_first_revision`. Only the final committed batch advances the durable revision. Large snapshots remain hydrating until the final barrier; delivery retries retain exact request bodies and receipt identities.
- IPC sink errors escape parsing and trigger observer reconnect rather than being treated as an accepted revision. Existing outgoing observation-only allowlist remains unchanged.
- Both IPC and rollout deliveries split by serialized bytes (7 MB) and event count (200), below the 8 MB HTTP request limit. Rollout cursor is saved only with the final batch, so replay after an intermediate failure is safe. Serialized visible text is bounded to 1.9 MB and truncation is explicit.
- Actual selected-source field-name evidence established nested `source.subagent.thread_spawn` genealogy and visible `Reasoning.summary_text`; these are supported while `payload.id` remains the distinct identity. Shared session IDs remain metadata.

Validation: `waypoint/.venv/bin/python -m pytest waypoint/tests/test_adapters.py waypoint/tests/test_adapter_incremental.py -q` — **23 passed**, 0.41 s. Unix socket access used the authorized sandbox escalation. This suite uses a synthetic Unix socket peer and real SQLite, not a live Codex connection.

Meaningful checks include a 1000-item history whose normal text patch reports visited containers=0, normalized items=1, rebuilds=0; subtree array shifts; unknown structure diagnostics; whole-state replacement; item identity change; exact/conflicting/stale revisions and gaps; 405-item multi-batch hydration with a deliberately lost durable receipt and exact retry; text coalescing/terminal flush; nested metadata; JSON-escaped Unicode/control text cap; and request byte limits.

Protective bounds are 32 MiB IPC frame by default, 100000 visited history containers per normalization/rebuild, path depth 128, cache 256 revisions. Copy-on-write patch application can still copy containing arrays; the item normalization measurement is not a claim of constant-time entire patch processing or a throughput SLA.

Live target comparison, owner disconnect/restart, natural root/descendant activity and installed-profile acceptance belong to the integrator's C05.4/C07 evidence. Synthetic results above must not be presented as proof of those live checks. No global Codex settings, other projects, skills, hooks, auth, or native execution state were changed.

## Bounded installed-source completion follow-up

Read-only selected-family structural inventory observed `event_msg.task_started` and `event_msg.task_complete`, each with its own native thread source and `turn_id`; terminal `SubAgentActivity` supplied `id`, `kind`, `agent_thread_id`, `agent_path` and no visible text/content/status. No message text was exported by the inventory.

Adapter now maps the thread's own `task_started` to running and `task_complete` to idle, retaining source timestamp, turn ID, reported-by source kind and historical provenance. Turn completion is not agent termination or work-plan completion. It does not cascade parent observations into children. Subagent operations retain original native metadata with empty text rather than an invented summary.

A source-cursor normalization version 2 triggers a one-time replay of each selected rollout source, preserving generation, file identity and source-location keys. Existing native message identity and ledger history remain intact; newly supported lifecycle evidence can be appended even if an older mapping had already consumed the file. The cursor advances transactionally as before.

Follow-up validation: `tests/test_adapter_incremental.py` — **13 passed**, 0.58 s, including native own-thread lifecycle provenance, absence of copied completion-message text, original subagent operation metadata, and real SQLite normalization upgrade/idempotent metadata replay. IPC socket code was unchanged after its earlier passing socket run. Integration owner separately adds the Store timestamp guard and historical activity presentation; current live acceptance remains in the C05/C07 target report.

## Observed reconnect defect and correction

The integrated live run exposed an `idempotency_conflict` after observer restart: persisted source generation was reused while the local event ordinal restarted, so a generated IPC receipt ID could repeat with a newly observed timestamp. Store correctly rejected the differing body; the owner source continued independently.

The bounded correction computes each generated observation timestamp once and includes it in its generated identity. Explicit persisted rollout record identities and timestamps retain the prior stable hash; prepared retry batches retain the exact original event bodies. A snapshot lacking provider runtime status now emits no activity observation, so absent data does not overwrite a child's native lifecycle evidence with an invented unknown state.

Focused validation after this correction: `tests/test_adapter_incremental.py` — **15 passed**, 0.83 s. New real SQLite regression recreates the normalizer with the same saved source generation and native snapshot at a different observation time: no receipt conflict, one native item projection, and an exact prepared retry remains idempotent. Explicit rollout identity remains unchanged. A missing-runtime snapshot preserves a previous native turn-idle observation. Integrator reruns the actual observer restart comparison separately; this contract regression is not the live recovery proof.

## Explicit fork identity boundary

The current native fork files contained verified child metadata followed by copied parent metadata/history. Actual own-child records resume after `event_msg.thread_settings_applied.thread_id` names that verified child. Outer timestamps had been rewritten and are not an identity boundary.

The collector now inspects only that native-ID marker, never its settings body. Copied parent evidence stays attributed to the selected verified fork parent; unknown identities remain quarantined. The exact matching native marker restores the verified child. Source cursor normalization version 3 replays selected files and persists this context across batches/restarts. Corrected own-child receipts use an explicit native identity suffix, while original source-location item IDs remain unchanged. Wrong old projections are addressed by the integrator's separate audited identity-correction event, preserving the ledger.

Focused validation after the fork fix: `tests/test_adapter_incremental.py` — **18 passed**. Checks cover copied-parent attribution, explicit child restoration, unknown identity quarantine, exclusion of settings content, stable source-location IDs, normalization upgrade with prior wrong-parent receipts, and a batch boundary followed by a recreated collector before the child marker. Live provenance and the private correction inventory belong to C05_LIVE/C07 evidence; this report contains no native IDs, message bodies, or credentials.
