# Acceptance and evidence plan

These are target obligations, NOT passed by creating this archive. Contract-model tests cover only the explicitly reported pure properties. Existing known-valid tests need not be rerun after unrelated prose changes.

| ID | Packet | Scenario | Expected observation | Evidence level |
|---|---|---|---|---|
| A01 | WPT-N01 | Native/profile round-trip | Old assignments/IDs/unknown fields and all retained history unchanged; new fields validated. | schema + actual Store round-trip |
| A02 | WPT-N01 | Migration interruption | Rollback leaves a usable prior DB; reopen and deterministic rebuild preserve accepted events. | real temporary SQLite |
| A03 | WPT-N02 | Inherited prerequisite regression | Nested /packet, authoring frontier and view report same ancestor/subtree requirement. | shared module + API |
| A04 | WPT-N02 | Partial dependency and phase | C05.3-like edge only affects relevant child/finish; independent preparation remains available. | graph fixture + UI endpoint display |
| A05 | WPT-N02 | Availability not status | Done without receipt is unknown; valid existing output can satisfy while parent status waits. | ledger + read projection |
| A06 | WPT-N02 | Stale evidence and conflicts | Predicate/workspace changes invalidate; layout does not; contradictory evidence is displayed. | event projection |
| A07 | WPT-N02 | Actual early work | Activity accepted and visible with missing/unknown prerequisite warning, no control RPC. | API + browser |
| A08 | WPT-N02 | Historical incident | Use actual IDs/version/chronology or explicitly NOT_RECONSTRUCTED; no speculative single cause. | target evidence only |
| A09 | WPT-N03 | Standalone task clarity | Human explanation names project context/change/outcome; technical instructions are in separate subtab. | content review + browser |
| A10 | WPT-N03 | One Plan/Map state | One block event updates both without another agent write; summary text identical to block intent. | real browser→HTTP→Store |
| A11 | WPT-N03 | Parent and history semantics | Waiting parent can show active descendants; parent/leaves not double counted; current runtime over old plan labelled. | synthetic fixture + browser |
| A12 | WPT-N03 | Project switching | Same node IDs in two projects remain separate; old late request cannot contaminate new project. | controlled delayed HTTP + browser |
| A13 | WPT-N03 | Catalogue cost/boundary | Only permitted registered projects; summary excludes raw messages and does not read every transcript. | API/SQL inspection |
| A14 | WPT-N04 | Filter before limit | One matching old item behind >1000 nonmatching ones is found by next-page query. | actual indexed Store |
| A15 | WPT-N04 | Paging identity | Equal first_seq ties, deep duplicate links and identity corrections do not lose/duplicate items. | Store + cursor tests |
| A16 | WPT-N04 | Cursor scope | Reused cursor under different project/filter/deep/version rejected; client deliberately opens new window. | API + browser |
| A17 | WPT-N04 | Reader autonomy | New matching count, scroll anchor, selected text and reader-specific filters remain correct. | real mouse/wheel/selection |
| A18 | WPT-N04 | Retention and unknowns | Hidden messages still ingested; unknown types accessible; encrypted reasoning not invented. | collector unchanged + projection |
| A19 | WPT-N05 | Algorithm association | One definition used by several blocks; right badge list and project inventory agree. | Store/view + browser |
| A20 | WPT-N05 | Implementation and stale tests | Planned/code/tested/measured states distinct; revision mismatch marks prior evidence stale. | event fixtures + UI |
| A21 | WPT-N05 | Optimization claims | Correctness required; incompatible dataset/method/unit rejects speedup; regressions retained. | reference oracle then runtime |
| A22 | WPT-N05 | Code/reference safety | Hostile strings escaped; no arbitrary read/eval/execution; snippets/links labelled by revision. | HTTP/UI security test |
| A23 | WPT-N06 | Known themes | Two known references preserved, errors/test states independent from accent, theme choice saved. | actual browser appearance |
| A24 | WPT-N09 | Actual third theme | Distinct owner-selected third reference implemented, all three available; not a duplicate slot. | owner reference + browser |
| A25 | WPT-N07 | Transferable authoring | Second project native profile accepted with its own IDs and no inherited MIXED permission. | schema + import/export |
| A26 | WPT-N07 | Skill behaviour and publication | Optional chat route remains optional; exact patches preserve unrelated rules; publication/install states explicit. | candidate review + repository validator + bounded workflow scenarios |
| A27 | WPT-N08 | Composed live system | Map/Plan/filter/algorithm/catalogue together on true browser/service and normal existing Codex events. | target machine |
| A28 | WPT-N08 | Recovery and cost | Reconnect/migration preserves new accepted events, bounded rich history observations and measured environment/n. | target machine + representative fixtures |

## Milestones
N01: native/profile round-trip and real isolated migration. N02: shared dependency contract/API parity. N03–N06: changed component checks with real input where interaction matters. N08: composed target checks once on accepted contributions. N09: only theme-affected checks plus final remaining acceptance.

Do not use a synthetic source event to mark an owner task done. An explicit completed packet receipt concerns the stated output; it is not proof of all deployment/appearance requirements.

## Invalidation
Profile/required-output changes invalidate the relevant migration/dependency checks; query/index changes invalidate filter/paging checks; reader/navigation changes invalidate interaction tests; source/normalization changes require affected native identity checks. Pure prose/position changes do not require a complete source campaign.

## Three independent labels
SOURCE_IMPLEMENTED: supplied code exists. TARGET_VERIFIED: the relevant actual chain was observed. OWNER_VISUAL_ACCEPTED: the owner reviewed the intended appearance. Do not collapse them into a single green flag.

N08 can conclude functional target verification with N09 explicitly open. The whole-stage visual requirement remains incomplete until A24. This is a delivery boundary, not a new restriction on agent work.
