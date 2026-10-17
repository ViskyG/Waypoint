# Acceptance plan: designed behavior, local evidence, target obligations

A successful fixture test proves its exercised contract, not universal runtime integration. These are checks of Waypoint, not gates imposed on the user's work map. A node may be marked done with red tests; a Waypoint release still needs truthful claims about its own tested behavior.

## Evidence available from this design pass

- `evidence/unit-results.xml` / `unit-tests.txt`: pure graph/merge contracts, real SQLite transactions/reopen/rebuild, FastAPI test-client boundaries, JSONL and framed IPC parser, **synthetic real Unix socket peer**, outbox. No real Codex involved.
- `evidence/browser-results.json`: actual Chromium mouse/keyboard interactions with the exact offline application assets and fictional data. 235px chat, pan/zoom/independent scroll, two nested levels, Up and ancestor breadcrumbs, camera restoration, theme changes, arbitrary status/acceptance/diff, off-map visibility.
- Browser navigation to localhost was denied by the container's administrator policy. No policy override was attempted. Allowed `set_content` was used for the UI; this does **not** establish browser-to-service integration. The normal-HTTP branch of `tests/browser_check.py` is supplied for the target.
- `evidence/http-results.json`: five actual localhost HTTP/service-lifecycle checks, independently of the browser, including committed long-poll, read/write capability separation and durable outbox recovery.
- Owner P09–P11 evidence in `sources/`: real existing VS Code IPC feasibility, one freshness sample, historical actual genealogy. Those are prior probe results, not a pass of the newly written adapter.

## Requirement-to-check trace

| Requirement | Local check / contract | Target acceptance |
|---|---|---|
| Observer never commands agents | IPC send allowlist tested; no execute HTTP route | Capture outgoing method names during natural run; assert no start/resume/steer/approval/stop. |
| One agent can cover many nodes | `scope.set`, multinode test | Real root/child use distinct IDs and overlap visible without reservation. |
| Shared session does not collapse descendants | metadata unit + prior P11 | Current target genealogy and caller-binding mapping use payload.id. |
| Real original messages in blocks | item projection + safe text renderer | Exact message text/type/ID matches provider source; no summarization/inference. |
| History not misbound to today's task | historical focus test; explicit correction | Hydrate existing work, then change focus; test straddling event with source watermark. |
| Large readable node stream | 235 CSS px + wheel test | Owner readability/ergonomics at normal desktop scale, continued updates do not steal scroll. |
| Arbitrary nesting / clear return | two-level real browser input tests | Third level and cross-scope edges; browser back and stored camera state. |
| Status separate from tests/activity | done+failed coexistence test | Broken channel shows unknown, not permanently live spinner. |
| Freely evolving plan | atomic 3-way merge/delete/new-ref tests | Real offline snapshot replay against changed local head, no unrelated Git writes. |
| Retired/off-map work stays visible | ghost + outside UI cases | Live work continues during plan removal; history remains addressable. |
| Reconnect without event duplication | event/cursor replay and revision gap tests | Disconnect collector socket only; source keeps working; reconnect/current message exactness. |
| Long sessions remain bounded | frame cap, traversal cap, virtualized visible cards | Actual large snapshot; memory/queue/data growth and responsiveness, no inference benchmark. |
| No secret/log export | package allowlist + no runtime directory | Review all returning file names/content; include aggregates and schema names only. |

## Target sequence: one integrated acceptance run

1. Start the supplied service in a private disposable Waypoint data directory. Run local unit suite; load the actual localhost UI. Import a **test** plan using the product schema. Do not alter the user's real project's source tree merely to test the observer.
2. Connect the supplied collector to an already working owner's root thread and its existing IPC/socket/rollout paths. Report actual CLI/extension/OS versions, source capability decisions and allowlisted method names. Do not start another App Server and mislabel it as the live owner.
3. Compare one or a few naturally occurring messages/tools against the source, including stable native IDs. Validate exact text projection locally; return only sanitized type/ID-equality evidence, not private message bodies. A timing sample remains n=sample count; do not infer an SLA.
4. Verify one root and real descendants already present. Historical tree verification is acceptable as history; do not label it simultaneous live behavior. Bind sparse focus signals to **the correct distinct executor**, then verify node and edge attribution for actual work. A source-watermark ambiguity must remain unassigned, not guessed.
5. Interrupt/restart only Waypoint collector/service. Confirm the Codex task continues independently, committed cursor/receipts recover and resumed partial item does not become duplicate chat messages. Check health/status distinctions. Do not stop actual agents.
6. Use the ordinary browser: nested graph, Up/breadcrumbs, raw messages, parent-stream toggle, scroll lock, themes, old-plan overlay, tests and expected/actual difference. Include reasonable real-size samples; report node/item count, hardware, browser and measurement method. The 100/300 simplified old probe is not a production FPS claim.
7. Close own subscriptions/service, inspect local state permissions, return `reports/RETURN_TO_CHAT_RU.md` and a sanitized evidence archive. Block only failed scope, retain already established results and exact diagnoses. Do not silently replace the chosen mechanism with a separate product.

No fixed requirement to spawn extra test agents or model turns. If a decisive live-child lifecycle cannot occur naturally, mark the untested step precisely and seek bounded authorization only if needed for that release claim.

## Release claim after target run

A claim such as “works with VS Code extension build X on this Linux environment, with these observed source fields” is justified by a successful recorded run. “Works with every Codex client/version”, “zero total token overhead”, “no possible loss”, “exactly once across arbitrary file mutation”, “production ready” and “complete raw internal reasoning” are **not** justified by this package.
