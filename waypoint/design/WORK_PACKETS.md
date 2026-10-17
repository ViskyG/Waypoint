# Coherent work packets for MIXED execution

These are component handoff contracts and dependencies, not an independently maintained second roadmap. Existing authored code must be reused. The session registry publication request uses these IDs. `DONE` below means the stated source artifact scope was produced; target integration is explicitly a separate packet.

## WPT-C01 — Local domain, plan and event contracts — DONE

**Produced:** `waypoint/domain.py`, `store.py`, `server.py`, `security.py`, `spool.py`, `client.py`, schemas and core tests. **Evidence:** local SQLite/merge/API/outbox tests plus standalone real HTTP lifecycle checks. **Residual:** target dependency environment and integrated deployment only. Do not rewrite this core merely because it was authored in chat.

## WPT-C02 — Observed native source reference — DONE

**Produced:** `waypoint/adapters/*`, `collector.py`, tests for actual Unix transport against a synthetic peer, owner evidence archive. **Scope:** implement the demonstrated profile as a testable reference without execution RPCs. **Not claimed:** current-owner live acceptance, every extension version, exact source-watermark attribution. Hardening work is bounded in WPT-C05.

## WPT-C03 — Shared visual reader base — DONE

**Produced:** `waypoint/web/*`, demo, preview builder and browser test. **Evidence:** actual input actions with offline app content. **Scope:** selectable nodes, themes, large chats, nested navigation, actor highlighting and plan differences. **Not claimed:** complete continuous-stream ergonomics/performance; see WPT-C06.

## WPT-C04 — Low-overhead agent workflow and handoff — DONE

**Produced:** CLI, two EN/RU skill candidates, deployment/acceptance docs, source/contract navigation. **Scope:** portable source contracts and exact commands. **Not claimed:** canonical skill publication/installation or native executor binding. Integration is target work, not a global instruction change performed by this design pass.

## WPT-C05 — Source binding, incremental normalization and durable attribution — READY

**Executor:** Codex in the owner machine, within MIXED. **Dependencies:** C01, C02, C04. **Read:** `CONTRACTS.md` §§1/4/5/7; `IMPLEMENTATION_MAP.md` source-hardening section; `ACCEPTANCE.md` target steps2–5; current adapter/collector tests; the original P09 script only to check a concrete protocol detail.

**Own:** `waypoint/adapters/*`, `collector.py`, source-specific tests and attribution additions in `store.py` with an explicit migration if needed. Do not edit web assets or unrelated project code. Preserve the command allowlist and selected-family boundary.

**Work:** apply the six-step indexed/coalesced normalization and verified identity/watermark route described in IMPLEMENTATION_MAP; establish the actual current IPC profile using existing natural activity; retain source-health diagnostics and stable acknowledgements. Fix only differences evidenced by the installed source. No new model runs, new agent tree or hook installation solely for testing without bounded authorization.

**Acceptance:** one actual owner message/tool matches the projected item; one distinct root/child binding cannot collapse through shared session_id; pre-focus hydration cannot be poured into current scope; a staged source gap invalidates freshness and resync restores it; collector failure does not stop Codex. Measure parser work/snapshot sizes with provenance, not an invented SLA. **Return:** source diff, tested profile version, exact sanitized commands/outcomes, remaining untested live lifecycle edges.

## WPT-C06 — Continuous live reader and rich-map performance — READY

**Executor:** Codex or authorized isolated chat preparation. **Dependencies:** C01/C03/C04. Can proceed alongside C05 only with separate physical ownership; coordinate any shared Store/API contract change before writing.

**Read:** ARCHITECTURE UI section, CONTRACTS read API, IMPLEMENTATION_MAP live reader/index section, `web/*`, `tests/browser_check.py`. **Own:** `waypoint/web/*`, browser tests, performance fixtures. The indexed Store query belongs to C05's owner or the integration owner by explicit agreement; do not edit it concurrently.

**Work:** live side-inspector updates, per-node frozen reading windows/new-message affordance, event-driven incremental repaint, target-side real HTTP browser tests, parent/child cross-scope edge clarity, native-ID copy links, and target accessibility/readability review. Keep message space >=235px at reading scale and both selected themes. Do not introduce agent-control UI or a compulsory timeline/minimap.

**Acceptance:** actual stream updates the open node and inspector without stealing scroll; Up/ancestors/browser back restore parent view at three nested levels; text selection remains possible; 100/300 representative rich nodes and a long stream are measured with viewport/DOM/sample count/machine recorded. Set budgets based on actual target measurements; no requirement to reproduce a decorative mockup pixel-for-pixel. **Return:** changed assets, browser evidence/screenshots, explicit performance and ergonomic limitations.

## WPT-C07 — One assembled target integration and delivery — READY

**Executor:** one designated local integration owner (Codex). **Dependencies:** C05/C06; all prior source packets exist. **Read:** CODEX_START, OPERATIONS, ACCEPTANCE and reports from C05/C06. **Own:** packaging, target config templates, integration tests and bounded compatibility fixes after other writers finish.

**Work:** install in a private environment; configure one source/API/UI; import an actual test roadmap; verify sparse block signals with real native identity; run the single target acceptance sequence; test observer-only restart. Resolve actual integration failures from preserved diagnostics. Finalize dependency lock for the actual interpreter. Candidate skill publication/installation requires the canonical library workflow and owner-authorized scope; do not silently overwrite global skills or scheduler bindings.

**Acceptance:** the owner's normal current client and the exact packaged implementation meet documented target behavior; no private logs/keys in returned bundle; outstanding limitations explicit. **Return:** `reports/RETURN_TO_CHAT_RU.md`, exact code revision, sanitized evidence archive, installation/uninstall instructions and current publication state. Code authored or a process merely started is not a completed live integration.

## Integration order and budget

Do C05 and C06 as coherent bounded work. Avoid per-class microtasks and repeated full-repository reading. Run focused tests for changed invariants, then one assembled acceptance in C07. A long test may permit safe independent work, not repeated polling through the model. Mixed policy does not authorize unrelated paid channels or launching a background worker here.
