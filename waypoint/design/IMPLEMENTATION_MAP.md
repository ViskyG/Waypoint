# Implementation map and remaining bounded work

## What this pass actually authored

This is a complete whole-system design plus a runnable reference implementation, not a claim of a deployed release. The reference uses the **same** server/client/contracts intended for development; `preview.html` embeds that client rather than introducing a second UI. The successful earlier Codex probes are included as source evidence. New adapter code was exercised with a synthetic real Unix socket peer, not the owner's live extension.

| Area | Supplied | Boundary |
|---|---|---|
| Plan repository | Schema, structural validation, immutable versions, exact retries, conservative three-way merge, structured diff | Real repository export/import acceptance remains target work. |
| Event engine | Transactional SQLite ledger/projections/cursor, item updates, metadata, focus, free status/results, checks, explicit corrections, source health | Cross-source identity is exact-ID-only; no guessed perfect deduplication. |
| Recovery | Bounded signal outbox, accepted-plan context, SQLite backup/rebuild, source generation/partial line handling | Actual live long-run pressure and rotating owner logs need target checks. |
| Source adapter | Exact observed IPC framing and allowlist, ownership check, snapshot/patch engine, reconnect, selected family read | Installed private schema compatibility, precise attribution watermark and performance hardening remain WPT-C05. |
| CLI/API | Local bearer capabilities, loopback Host/Origin boundary, packet/import/export, signals, foreground observer | Integration must provide correct distinct executor identity. |
| Interface | Two themes, recursive map, proper Up/ancestor navigation, retained camera, large chat, actor highlights, side tabs, versions/diff, ghost/off-map | Continuous inspector refresh, incremental repaint and final rich-map performance remain WPT-C06. |
| Agent skills | Two small EN/RU candidates, use and installation boundaries | Not published/installed/behaviorally validated in live Codex. |
| Verification | Unit/contract, synthetic socket, real standalone HTTP/restart, real offline Chromium input tests | Browser→localhost blocked by container policy; normal route supplied for target. |

## One source pipeline, not two implementations

IPC observes current revisioned activity; JSONL supplies persisted history and genealogy. Both feed `Normalizer` and the one Store/API/UI. Lack of official App Server socket does not make a new architecture necessary. Missing compatibility is diagnosed at that provider boundary.

The final product implementation should retain the plain browser renderer unless actual integration shows a material need for a different graph library. A library replacement would be a renderer module change, not a new plan or event domain. No React Flow Pro dependency, purchase or performance claim is assumed.

## Required hardening of the reference source adapter (WPT-C05)

The current reference deliberately walks known history containers and fingerprints items after each accepted state update. It is simple and testable but not the final long-conversation fast path. Implement this chosen path without changing public contracts:

1. On initial snapshot, index each known native item by `(agent_id,item_id)` and container path; traverse only the observed history roots, never settings/arguments as arbitrary messages.
2. On a patch, find the closest indexed item ancestor of each changed path. Re-normalize those items only. A container add/remove invalidates only its subtree. An unknown structural patch requires one bounded rebuild of that history-root index with a diagnostic, not a silent incomplete stream.
3. Coalesce nonterminal text revisions over a small configurable interval (proposed 200 ms). Preserve exact provider text of the emitted revision; no LLM summary. Flush terminal item changes immediately. The product preserves messages and meaningful operations, not a guarantee of every token animation frame.
4. A source revision is acknowledged only after its necessary normalized records are committed. A sink failure discards that pending acknowledgement, marks health, reconnects/hydrates and uses stored file cursors. Partial acceptance across a large snapshot must remain visibly hydrating until its final barrier.
5. Create a verified per-executor binding using the current provider's native thread ID. Do not infer identity from shared session or inherited environment. The current explicit `--agent` interface is the integration seam. A binding file/launcher shim must be project-local and supplied by the existing executor integration, not an observer that takes over agent creation.
6. At focus changes, record the source's committed revision/item watermark. Existing items keep their association; a later hydration or ambiguous straddling item remains unassigned until evidence permits attribution. Enrich the internal attribution metadata, preserving the existing sparse signal envelope.

This is the concrete selected implementation route, not a request for Codex to redesign source identity from scratch. The source archive contains working P09 requests to compare against actual fields. Real user messages are never copied into returned debugging evidence.

## Required completion of live reading/performance (WPT-C06)

Keep source data and view state separate. Maintain per-node read windows. If a reader is at the latest message, append/update and keep them at the bottom; if reading older text, preserve that window and show a small new-message affordance. Apply the same rule to the side inspector, which the reference currently leaves stable rather than refreshing its message list.

Drive incremental invalidation from committed events: node state/check changes update that card, item revision changes update only that item projection and its mapped cards, actor changes update the affected strip/regions, plan.changed updates topology. Pan/zoom culls mounted rich cards, while overview mode preserves topological footprints. Do not mount a full 500-message DOM for every node.

For large histories add indexed `item_targets(project,agent,item,target_kind,target_id,first_seq)` associations in a real migration, updated in the same transaction as item projection/link correction. Query target associations before fetching message bodies. Descendant scopes can be chunked to bounded SQL parameter sets and merged by stable first_seq; do not assume optional SQLite JSON features. The reference's direct body scan is adequate for the delivered test corpus, not a benchmark of this final index.

Preserve explicit messages when native IDs cannot reconcile sources. Group possible duplicates only as a reversible display hint, never destructive text-hash deduplication. Old plan mode labels current activity; it is not time travel.

## Non-goals kept out

Agent/task launching, approvals, resource scheduling, remote fleets, always-on cloud sync, workflow-enforced status transitions, compulsory minimap, full replay timeline, model-generated status summaries and public release automation. No new monitoring platform or multi-service stack is needed.

### Recent-revision consistency
The reference ignores a previously seen or older IPC revision; it does not retain all corresponding patch bytes. C05 should retain a bounded recent `(revision, canonical-change-hash)` cache. An exact duplicate has no effect; a different change with the same cached revision marks the stream inconsistent and requests a full snapshot. Revisions older than the cache remain stale observations, not proof of byte-level consistency. This is separate from the service event-ID conflict guard, which is already implemented and tested.
