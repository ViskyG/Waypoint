# Waypoint — design 1.0

**Decision authority:** owner's Design Context, read on 2026-10-16, including MIXED and the final pre-Pro audit. This document is a new design, not a verbatim source summary. Source observations, owner requirements and design choices are distinguished below. One product, one event model, one roadmap; not a primary and a speculative replacement system.

## 1. Whole-system view

Waypoint is a local observer of work, not an executor. A user opens a roadmap, reads the assignment on the left and acceptance on the right, follows agents on the shared graph and inspects original available messages. An agent may modify its plan, work across nodes, finish with failed tests, create descendants or work outside the map. The observer records these facts without granting or refusing permission to work.

The selected initial deployment is one user-owned Python service on Linux, SQLite on the same local machine, and a browser interface served by that service. The browser uses plain ES modules with HTML nodes over SVG connectors. This builds on the tested UI interactions without purchasing React Flow Pro or adopting a graph editor solely for passive viewing. This is a designer choice: the UI renderer is isolated from the domain model and can be replaced without changing protocol, data or skills. It is NOT a claim that React Flow is too slow.

The application has four logical modules, not four independent services. The native collector runs in a separate foreground process for isolation and writes to the same local API/ledger:

1. **Plan repository:** immutable versions of work graphs; guarded imports and structured differences.
2. **Observation engine:** source adapters, source checkpoints, identities, normalized items and evidence-bearing associations.
3. **Read model:** current map, active agent areas, original message streams, results and independently reported test evidence.
4. **Local API + CLI + web:** quick agent signals and browsable read-only views. No generic proxy to Codex and no execution endpoint.

SQLite is the transactional working store. Git receives explicit plan checkpoints; messages and authentication data never enter Git by default. Exported plans and imported change packages are ordinary files. A prepared package is not an applied update. No continuous cloud calls and no inference are required for observation.

## 2. Inputs selected from evidence

P09 established live observation through the existing VS Code extension's **private Unix IPC**, not a new official App Server listener. P10 matched one terminal item between IPC and the actual JSONL file; its timing is a single detection comparison, not a latency distribution. P11 established real historical parent links using `payload.id` and `payload.parent_thread_id`; siblings may share `session_id`. These are the primary basis for the first integration. See `sources/INPUTS.md` and the supplied probe archive.

Both IPC and rollouts feed the same engine. IPC supplies live snapshots and revisioned patches; JSONL supplies persisted history and identity/family metadata. They are complementary input channels, not duplicated product implementations. There is no reason to build an alternate observer based on untested official subscriptions. The official App Server transport may be added later if actually needed; it is not part of the initial critical path. Hooks are not required for v1.

Existing probe scripts are **evidence/reference code**, not production daemons: they lack complete reconnect, bounded buffering and long-running correctness. The adapter implementation must preserve their observed wire format, while adding these operational boundaries. Do not modify the user's extension, global Codex configuration, credentials or the running agent to make an adapter work.

## 3. Independent state dimensions

Do not collapse these into one `status`:

- **Plan:** requirements, acceptance, dependencies, nesting and geometry for a named revision.
- **Agent assertion:** arbitrary status text, result, expected/actual difference, optional estimate.
- **Observed activity:** source-confirmed running/idle/ended/unknown state, timestamp and source.
- **Check evidence:** last outcome, planned case identity, source/code/environment basis and freshness declaration.
- **Observation health:** connected/stale/gap/unsupported/error; says what the observer knows, not whether work stopped.

An `ended` parent does not end its descendants. `done` does not recolor a failed test. A source disconnect does not change the agent's declared result. A cyclic dependency is a map warning, not a scheduling gate. Structural nesting must remain a finite tree to be navigable; malformed nesting updates are rejected atomically, while actual observation continues.

## 4. Identity and graph semantics

Namespace identities by installation/source family and project. Native thread ID identifies an agent session; shared container session ID, parent, task path and fork ancestry remain distinct fields. Never merge two agents merely because `session_id`, title, cwd or message text matches. Missing parent records become unresolved references, not fabricated ancestors. Parent cycles are diagnosed and traversals have visited sets.

A block has one permanent, preferably readable ID (e.g. W-03), unique within its project. This is both the protocol key and the human reference in the delivered schema; a second opaque identifier is not required. It contains an assignment, acceptance criteria with stable IDs, planned tests, optional source links and an optional parent block. IDs are never recycled for different work. Moving, renaming or expanding a block keeps its identity. An edge has its own ID, source and target block and means “source work is a declared dependency of target”. An edge may itself have associated messages.

Nesting and dependencies are different. Horizontal extension and vertical refinement are explicit layout hints, not inferred solely from coordinates or the presence of tests. A parent can have parallel horizontal lanes, with successive refinement steps below each lane. Links may cross nesting levels. At a collapsed scope they are projected to visible ancestors and grouped; the original edge IDs remain inspectable. Auto-layout preserves existing geometry where possible; new source messages must never shuffle the map.

Agent↔block and message↔block/edge are many-to-many relations. Regions are soft visual envelopes around an agent's currently associated nodes. They do not reserve tasks or claim exclusive ownership. Unknown or retired references remain visible in the actor stream and “Outside map” area.

## 5. Attribution without extra inference

Passive telemetry alone does not reveal which arbitrary W-03 the user intended. Do not claim otherwise. The deliberate bridge is a sparse **focus signal**, emitted only when the working scope changes. The designed executor integration binds the local CLI to a verified native agent ID once; it must not blindly use a shared container session or an inherited parent binding. The delivered reference requires explicit `--agent`; verified automatic caller binding is the bounded C05 completion task. Child bindings are distinct.

`wp ... focus W-03 W-04` begins a new scope for that agent. Native messages are not re-written or sent twice. The selected final contract records an attribution boundary and the source watermark known at the time. The reference currently records a timestamp boundary; source-watermark implementation is assigned to C05. An explicit item/edge association overrides the fallback focus. Late history hydration is marked historical and is not retrospectively poured into today's scope. Ambiguous order remains unassigned until an explicit correction; the UI prefers an honest unassigned message to a convincing wrong attachment.

Completion/acceptance/test metadata can be sent in one ordinary tool call alongside the actual work. There are no heartbeat reports generated by a model and no repeated model polling. Agents receive only a local task packet and relevant references, never the full archive of conversations. A telemetry failure cannot abort a build or the agent's actual task: `emit` queues a bounded local receipt for later import, while invalid **plan mutation** fails explicitly and does not claim success.

## 6. Durable events and streaming updates

A received observation is an immutable event with an idempotency key. Identical replay returns the original receipt. Reusing an event ID with different payload is a conflict; it is not silently ignored. In one SQLite transaction: store event, update projections, store source cursor, allocate a commit sequence. Readers see before or after, never a half-applied event. Multiple writers serialize in the service; SQLite remains a local single-writer system, not a distributed database.

Native items are projected once using proven source IDs and scope. IPC partial text replaces the current item projection; it is not appended as another chat message on each token. Proven cross-source IDs may share an item key. If identifiers cannot be reconciled, keep separate evidence with a possible-duplicate hint; never deduplicate unrelated repeated messages by text alone. The source event log retains provenance and accepted item revisions for projection rebuild. One canonical projected item is shared by all associated cards; this is not a promise that historical event records contain no repeated text or that every provider token is losslessly retained.

IPC patches apply to the exact `baseRevision`. Already-seen or older revisions are ignored without reapplying them. The reference does not retain a patch fingerprint for every prior revision and therefore cannot prove that a repeated revision has identical content; final source hardening should detect a contradictory recent revision with a bounded fingerprint cache and resynchronize. A forward gap or invalid patch invalidates that stream's projected freshness and requests a new snapshot. Apply patch batches to an isolated candidate state: one bad operation must not half-mutate the last good snapshot. Reconnect uses exponential backoff with a cap. Source decoder and queues have byte/item bounds; oversized state produces a visible health problem, not uncontrolled memory growth or false “current” status.

JSONL cursors include file identity, generation and complete-line byte offset. Partial trailing lines are retained until complete. Truncation, inode replacement and prefix changes create a new generation; backfill deduplicates only where IDs justify it. Unmarked data that disappeared before observation cannot be recovered or even reliably detected: do not advertise exactly-once delivery from arbitrary external logs.

The browser receives sequence-based change notifications. The reference refreshes a bounded read model; C06 completes affected-card/item invalidation and continuous inspector updates without replacing this client or API. On reconnect it can request events after its last committed cursor; if unavailable it requests a fresh read model. Slow browsers cannot back-pressure an agent. Scroll position and zoom are local view state, not events in Git.

## 7. Plan versions, changes and Git

Every substantive graph update declares a base version and request ID. Same request/payload has the same receipt. The current plan head is advanced only after validating the candidate atomically. Node/edge/criterion dictionaries are keyed by stable IDs so field-level three-way comparison is meaningful. A concurrent deletion versus edit, or deletion versus new reference, is a conflict; disjoint fields merge. Arrays of prose are atomic unless the schema provides IDs. No last-write-wins by clock.

A retired node remains in older plan versions. Live observations still referring to it are displayed as **ghost work** with an old-plan badge. By default, a current node view shows history of that identity but labels results evaluated against an older acceptance version. Selecting an old plan does NOT pretend that the current live agents were executing at that old time. Plan history and runtime time travel are separate; time travel is outside v1.

Git export is an explicit deterministic projection, excluding runtime messages. Use `wp ... plan-export` into a scoped file, then the project's normal commit/push workflow; the observer does not spawn periodic Git commits or resolve unrelated merge conflicts. An offline ChatGPT packet includes `base_version`, patch/snapshot and provenance. Import computes conflicts before committing any mutation and returns a structured conflict if they cannot be safely reconciled. Existing project files and non-Waypoint changes remain untouched.

## 8. UI contract and selected reversible decisions

Use one shared map as home; active agents above and nested orchestrators on the left. Same actor appears in both locations when it delegates. Clicking an orchestrator highlights its transitive descendants, with matching readable markers; completed actors remain accessible but muted. The right inspector opens requirements, acceptance/diff, full stream or actor details without changing execution.

Choose these reversible defaults (designer decisions, not previously confirmed user answers): an “Outside map” drawer; parent stream includes descendants with a toggle for direct-only; active retired nodes appear as ghosts. These do not constrain agent behavior.

At reading zoom each block allocates at least about 235 CSS px to messages; permit expanding it further. At overview zoom hide text content but keep a stable node footprint, status and lamps. The wheel inside an expanded chat scrolls messages; outside it zooms about the pointer. Dragging blank canvas pans; text selection and controls must not initiate a drag. New messages do not auto-scroll a reader who has scrolled away; show a count and “latest”. Center/header activation opens nested work; using the chat itself selects text/scrolls, not accidental navigation.

Ancestor breadcrumbs and a visible “Up” button operate at every depth and restore previous scope's camera. Browser back changes view, not plan data. Node links include map and block identity so the user can point an agent to W-03 or W-03/acceptance/A-02. Never rely on only Backspace.

Two appearance directions: light Terracotta and dark Obsidian, with shared semantic tokens. Crimson is an accent, not the universal success color. Tests retain distinct pass/fail/not-run/unknown marks and text accessible on focus/hover. No giant decorative backgrounds, repeated static labels, obligatory cost counters, timeline or minimap. UI text is Russian initially; code/contracts and canonical skills English with Russian companion instructions.

## 9. Local safety boundary

Bind to loopback only by default. Validate Host/Origin; separate read and write capabilities. Browser gets read access, not a generic operation console. Credentials are generated locally, not embedded in this package or a repository. Native IPC sends only the observed initialize/owner-discovery/history-follow and follow/unfollow messages; never start/resume/steer/approve/stop. Replies to discovery declare `canHandle:false`.

Collect only explicitly selected projects and thread families. All raw provider-visible content is sensitive: local data directory is user-private and outside Git. Render messages as text, disallow executable Markdown/HTML and remote image fetches. Encrypted reasoning is neither decrypted nor reconstructed. Full content is local; default report/export contains plan and sanitized metadata only. An explicit private export is a separate action, not a silent cloud sync.

## 10. Scope and expansion

v1 includes the roadmap, nested viewing, text-first work history, actors/families, sparse signals, checks/results, plan history/import/export, and integration with the proven VS Code/rollout mechanisms on this Linux installation. No scheduler, task launcher, chat composer that sends to agents, remote fleet, authorization hierarchy, always-on GitHub polling, or separate alternate implementation. New providers implement the same normalized input boundary later.

Minimum product claims require local unit/contract/UI evidence plus target live acceptance of this implementation. Existing Codex probe success is valuable evidence of feasibility but does not validate newly written code. `design/ACCEPTANCE.md` will assign exact checks and distinguish tests executed here from work for the owner's runtime.
