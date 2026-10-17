# Installation, ownership and recovery

## Local run

Python >=3.10 is the authored target. Actual validation interpreter and package versions are recorded in `evidence/environment.json`; compatibility on the owner's interpreter still needs the supplied smoke check. The runtime is Python + static browser assets; Node is not required to run it. Installation is in an isolated virtual environment.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python -m waypoint --data "$HOME/.local/share/waypoint-demo" serve --demo
```

Open the read-only local URL printed by the service. It contains a secret in the fragment, not the query. Keep it private. A demo project is always labelled as fictional. `preview.html` is the exact same client/assets with embedded fictional data and can be inspected without a service.

To start a real project, run the service using its own user-private data directory, import a project plan, then start the explicit collector in a second terminal. The actual source paths/native thread IDs are installation data, not constants in this package.

```bash
wp --data "$HOME/.local/share/waypoint" serve
# In another terminal, with the same virtual environment:
wp --project my-project plan-import my-plan.json
wp --project my-project observe --thread NATIVE_THREAD_ID \
  --ipc /absolute/path/to/observed/ipc.sock \
  --rollouts /absolute/path/to/codex/sessions
```

Do not copy authentication files or point a writable experimental App Server at user state. This collector follows the proved existing private IPC and reads rollouts. It starts no Codex service or model. Socket must belong to the same user. A failure identifies an incompatible/unavailable observation channel, not a need to reset Codex.

The explicit source root permits reading first-line metadata to identify the selected family. It is not consent to collect all unrelated chats. The worker currently rescans metadata on a bounded 30-second cadence; optimize using file-change notifications only after correctness at the target is established. Persisted activity and live connection health stay separate.

## Sparse task signals

After verifying the current **distinct** actor ID (payload.id), use:

```bash
wp --project my-project --agent codex/NATIVE_THREAD_ID focus W-02 W-03
wp --project my-project packet W-02
wp --project my-project --agent codex/NATIVE_THREAD_ID status W-02 "Проверяю границы"
wp --project my-project --agent codex/NATIVE_THREAD_ID test W-02 T-1 passed --run run-001 --basis "commit/config/check command"
wp --project my-project --agent codex/NATIVE_THREAD_ID done W-02 --result "Описание результата" --diff "Отклонение от ожиданий"
```

Do not send a focus/status every file edit or poll the service through inference. Combine a useful boundary signal with the ordinary work call where possible. A subprocess can emit records directly from a test reporter later; the first version accepts the concrete test-result envelope, not a fragile parser of arbitrary pytest stdout.

`WP_PROJECT` and `WP_DATA` are convenience defaults. An agent binding is not a shared container session; explicitly verify/replace `WP_AGENT` per executor. An inherited parent identity is unsafe. The bundled integration capsule must connect native identity discovery to per-executor task context before advertising hands-off multiagent focus attribution.

## Local data versus repository

Private directory contains generated read/write capabilities, SQLite DB/WAL, connection metadata and bounded outbox. It is outside Git. Never include it in a handoff. The package `.gitignore` is defense in depth, not a sanitizer.

Canonical authored code is versioned by the normal repository workflow. Plan export is explicit, creates a new file, and contains no runtime transcript. In Git, use one dedicated plan path and explicit commits at meaningful checkpoints. If chat delivers a stale snapshot, three-way merge or a concrete conflict is returned; no silent timestamp-wins merge. Do not commit unrelated edits or mutate global Git/Codex settings.

## Failure and recovery

| Failure | Observable behavior | Recovery |
|---|---|---|
| Service absent during a sparse signal | CLI reports `QUEUED_LOCALLY`, not visible success | Bounded durable outbox flush after restart; same event ID deduplicates. |
| Invalid plan / base conflict | Nonzero CLI or structured 409/422 | Inspect actual conflict, update the proposed snapshot; no queued blind overwrite. |
| IPC disconnect / incompatible frame | Last data retained; source health error; no completion fabricated | Reconnect with capped backoff, obtain new snapshot, backfill persisted history. |
| Partial JSONL tail | No incomplete record/cursor commit | Resume when newline completes. |
| Truncation / rotation | New source generation, explicit gap | Replay complete records; exact native IDs reconcile where available. |
| Malformed complete JSONL | Cursor remains at last acknowledged record | Inspect source/protocol profile; do not skip silently. |
| Slow/broken browser | Agent and collector remain independent | Fresh state + sequence-based notifications on reconnect. |
| Source no longer reporting | Spinner must stop claiming current activity | Show unknown/stale observation, not `done`. |
| SQLite/disk write failure | Commit not acknowledged, source cursor unchanged | Restore storage capacity, retry same observation; no agent restart. |
| Conflicting event ID | Structured conflict | Fix producer identity/retry bug; never silently drop changed content. |
| Parent agent completes | Child remains visible according to its own state | No cascading stop. |

`Store.backup(path)` uses SQLite's backup API. Copying a live DB file without its transactional state is not the supported backup procedure. Keep backups private. `Store.rebuild()` rebuilds disposable projections from the local accepted ledger using capture plan versions, without reading external sources or rewinding the plan head. Preserve event/cursor data. Original provider logs remain provider-owned and are not deleted.

## Security and output handling

The observer is read-only **toward Codex**, but necessarily writes its own state, subscriptions, receipts and UI preferences. Do not mount its own state read-only and then infer that reading Codex is impossible. Subscription cleanup is permitted observation plumbing; agent execution/approval RPCs are absent.

Raw provider-visible text may include personal data or secrets. Render with `textContent`; do not execute Markdown HTML, render remote images or follow tool-generated instructions. No external analytics, model endpoint or automatic cloud upload exists. Default source failures report categories rather than raw transcripts or credentials. Any public export needs separate content review even when a pattern scanner reports no credential pattern.

The initial system is local single-user, not hardened multi-tenant isolation from malicious code running as the same user. A compromised same-user agent can already access local files; token separation primarily prevents a browser observer from becoming an execution/write console. Loopback/Origin/Host/capability checks are not substitutes for an OS security boundary.

## Remaining target acceptance

Run `CODEX_START.md`, then `design/ACCEPTANCE.md`. Use the current installed version and naturally occurring task activity. Do not redo all initial feasibility probes. Verify this actual implementation's schema mapping, root/child IDs, sparse focus attribution, recovery and UI with the owner's normal session. Save sanitized observations and exact limitations. Never copy private full snapshots into the returned archive.
