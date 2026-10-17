# Evidence report — Waypoint design and reference implementation

Date: 2026-10-16. This is evidence from the present design pass, not a claim that Waypoint is installed on the owner's machine. Exact tested code is the code in this package's `MANIFEST.json`.

## Executed checks

| Check group | Result | Scope and artifact |
|---|---|---|
| Python unit/contract suite | **36 passed** | `unit-results.xml`, `unit-tests.txt`. Real local SQLite transactions, reopen/rebuild/backup, guarded plan merge, event identity/cursors, outbox, API permissions; synthetic source data and a real Unix socket with a fabricated peer. |
| Chromium interaction suite | **23 checks passed**, no JavaScript exceptions | `browser-results.json`. Chromium 144.0.7559.96; actual mouse/keyboard actions on the exact application assets with fictional data using allowed `set_content`. Ran again after final JS/CSS formatting. |
| Actual local service lifecycle | **5 checks passed** | `http-results.json`. Real localhost HTTP, authenticated write/read, commit waking long-poll, browser read capability denied writes, absent-service CLI spooling and service restart/drain. No browser and no Codex used in this group. |
| Wheel packaging | **PASS** | `packaging-build.json`. Built with `pip wheel --no-deps --no-build-isolation`; verified CLI entry point and packaged web assets. This is not target installation. |
| Python compatibility | **3.10 grammar check passed** | `python-compatibility.json`. Actual execution was on Python 3.13.5; Python 3.10 runtime and dependency installation were not exercised. |
| Generated schemas | **PASS**, within Python suite | Plan/event example checks, schema parsing and OpenAPI generation. Cross-reference and nesting semantics are additionally validated by code. |
| Source syntax and package integrity | **PASS at packaging** | Python compilation, JS syntax check, JSON parsing, referenced package files, file SHA-256 manifest and ZIP CRC are recorded in the delivery validation. |

The test groups have different meanings; adding their counts does not produce a percentage of product completion. Test names, commands and observations are retained in the machine reports. Rendered screenshots in this directory are from the actual delivered UI, not image generation.

## Browser transport limitation

Navigating the test browser directly to localhost returned `net::ERR_BLOCKED_BY_ADMINISTRATOR`. The browser's configured policy was not overridden. Browser content was tested through the available `set_content` operation; real localhost HTTP was tested separately by a non-browser client.

This establishes UI input behavior and service HTTP behavior **separately**, not end-to-end browser-to-service integration. The target branch of `tests/browser_check.py` is supplied for that remaining integration. See `browser-http-limitation.json`.

## Prior evidence used, not repeated

Owner-provided P09–P11, preserved in `sources/feasibility-evidence-v3.zip`, established access to the actual existing VS Code private IPC, one matched terminal-item freshness comparison, and historical real parent/child/grandchild identities. Those observations are the basis of the selected design.

The newly written collector was **not connected to the owner's real Codex in this pass**. A fabricated Unix peer passing a protocol test is not a repeat of P09. The old single latency observation is not a guarantee about this new implementation.

## Implemented reference versus target completion

C01–C04 are completed **source deliverables in their stated scope**: local contracts/store/API, observed-profile adapter reference, common visual client, sparse CLI and draft skill handoff. They are not a claim of finished deployment.

C05 completes verified native caller binding, source-watermark attribution, dirty-item normalization/coalescing and durable stream acknowledgement. C06 completes continuous inspector/message-window updates and representative rich-map performance. C07 performs one assembled target integration, including real browser HTTP. The algorithms, shared contracts, file ownership and acceptance conditions are specified in `design/IMPLEMENTATION_MAP.md` and `design/WORK_PACKETS.md`.

The reference currently uses conservative timestamp-based scope attribution, bounded full-state normalization and bounded read-model refresh. These are explicitly not claimed to implement all final continuous-stream behavior. No second observer architecture is required to complete the selected design.

## Defects found and corrected during this pass

The local checks prompted corrections to parent reference validation, malformed private patch handling, replay/source generation behavior, scope/historical ordering, API security paths, caught UI refresh error, and theme rendering. Final machine reports refer to the corrected package. Old failing scratch output was not relabelled as success; final passing checks were actually run.

## Actions not performed

No new Codex run or model inference; no agent spawning; no write to the owner's application repositories, global configuration, hooks or skills; no deployment; no modification of provider history/auth files; no Pro output write to Drive. Library registry/inbox were inspected but not modified because this session exposed no Library write action. See `handoff/PUBLICATION.md`.

No claim of universal client compatibility, production durability, full accessibility audit, lossless raw token capture, zero total token cost, secret-free arbitrary user logs, or public-release readiness is made.
