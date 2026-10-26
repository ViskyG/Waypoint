# Waypoint

**A local work map for following Codex tasks, agents, and results.**

[Русский](README_RU.md) · [Project skills](#project-skills-and-trackable-work) · [Try the demo](#try-the-demo) · [Connect Codex](#connect-codex) · [Documentation](#documentation)

Waypoint brings your development roadmap and observed agent activity into one browser view. Follow dependencies, see which task an agent is working on, read the original messages, and inspect the evidence behind a completed task.

It is built for developers who work with Codex and parallel subagents and want to keep the plan, the work, and its results connected. Waypoint runs locally and observes an existing session. You continue to launch and direct your agents through your usual tools.

![Waypoint observing its own development: a task graph, agent hierarchy, original messages, and completion indicators](docs/images/waypoint-map.png)

*An actual local installation observing work on Waypoint itself. Screenshot supplied by the project owner. It shows the Russian interface; new browser profiles default to English, with English / Русский available in the header.*

## Why Waypoint

As a project grows, the roadmap, agent conversations, and test results can end up in different places. Waypoint gives them a shared context:

- **Follow parallel work.** See agents, their parent–child relationships, and the tasks they have explicitly declared as their current scope.
- **Understand progress.** Inspect the original conversation and available tool events attached to a task.
- **Review completion.** Read the reported result, check outcomes, run IDs, and evidence references together. Completion status, check results, and agent activity are separate signals.
- **Keep continuity.** Preserve accepted history and plan versions in a local SQLite journal across restarts.

## What you can explore

| View | What it shows |
|---|---|
| **Projects** | Project purpose, observed activity, and source health |
| **Map** | Nested tasks, dependencies, scope navigation, and message streams |
| **Plan** | Task intent, executor instructions, prerequisites, results, and checks |
| **Agents** | Agent hierarchy, current scope, and work outside the map |
| **Algorithms** | Definitions, code references, recorded correctness evidence, measurements, and comparisons |

Message filters help you read long histories. Reader position, text selection, and open detail panels are preserved during supported updates and language changes. The interface offers **English and Russian**, plus **Terracotta and Obsidian** themes.

Waypoint is a **passive observer**. It does not schedule, launch, stop, or approve agent work. Checks and evidence are recorded observations; a green status alone is not proof that a result is available or correct. Unknown attribution and stale evidence remain visible.

## Project skills and trackable work

**A trackable project needs a compatible roadmap and executors who connect their work to it.** The skills below give the planner and agents those instructions. Starting the viewer or connecting an observer does not automatically assign conversations to task cards.

### Included in this repository

| Role | Instructions | Responsibility |
|---|---|---|
| Roadmap planner | [waypoint-map](waypoint/skills/waypoint-map/SKILL.md) · [RU](waypoint/skills/waypoint-map/SKILL.ru.md) | Prepare one dependency graph with stable task IDs, readable intent, executor assignments, acceptance/test IDs, prerequisite outputs, and evidence expectations |
| Executor and every subagent | [waypoint-observe](waypoint/skills/waypoint-observe/SKILL.md) · [RU](waypoint/skills/waypoint-observe/SKILL.ru.md) | Verify the executor's own identity, declare task scope, record actual checks and results, and release scope at handoff |
| Planner, executor, and reviewer | [WAYPOINT_WORKFLOW.md](next-stage/skills/conformance/WAYPOINT_WORKFLOW.md) | Share the exact CLI protocol, evidence levels, roadmap update rules, and completion discipline |

The project skills are bundled as **waypoint-map 0.3.1** and **waypoint-observe 0.3.0**, both `draft-candidate`. They are available for explicit project-local use; they are not automatically loaded by Waypoint, globally installed, or registered in the external skill library. Reading a skill does not start an agent or grant execution permissions. See the [integration boundary](waypoint/skills/INTEGRATION.md).

### Apply the profile to a project

1. **Prepare the map.** Give the planner `waypoint-map` and the shared workflow. Start from the [project template](roadmap/templates/PROJECT.plan.json), adapting its sample requirements and project ID. Produce one [compatible plan](waypoint/schemas/plan.schema.json), with explicit dependencies and observable acceptance criteria.
2. **Import and connect.** Import that plan into your local Waypoint and observe the real Codex session as described in [Connect Codex](#connect-codex). The plan defines intended work; the event journal supplies observed activity, status, results, and checks.
3. **Connect each executor's work.** Give the executor `waypoint-observe` and the shared workflow before work begins. Each agent, including every subagent, verifies its own binding and declares `focus` for the relevant task IDs. Messages observed within that declared scope can then appear in those task cards.
4. **Record and preserve the result.** Register actual outcomes under the plan's existing test IDs, attach evidence with its run/revision, record the result before completion, then clear or change `focus`. Update an existing map from a fresh export, preserving IDs and history.

For example, explicitly include the following in a planning task. Resolve these paths from your Waypoint checkout:

```text
Use waypoint/skills/waypoint-map/SKILL.md and
next-stage/skills/conformance/WAYPOINT_WORKFLOW.md as project-local instructions
for this project. Produce a Waypoint-compatible roadmap with stable task/test IDs,
explicit dependencies, and evidence expectations. Keep one source plan.
```

For an implementation task:

```text
Use waypoint/skills/waypoint-observe/SKILL.md and the shared WAYPOINT_WORKFLOW.md
from the Waypoint checkout for this project. Work from the imported task packet.
Verify your own binding and declare focus before work; every subagent does the same.
Record actual checks and evidence before completion, then release your scope.
```

### General roadmap skills

If your workflow uses [ViskyG/agent-skills](https://github.com/ViskyG/agent-skills), pair the project profile with the relevant general skill:

- Planning: [build-implementation-roadmap](https://github.com/ViskyG/agent-skills/blob/main/skills/chatgpt/build-implementation-roadmap/SKILL.md) + `waypoint-map`.
- Codex implementation: [execute-roadmap-efficiently](https://github.com/ViskyG/agent-skills/blob/main/skills/codex/execute-roadmap-efficiently/SKILL.md) + `waypoint-observe`.
- Independent review: [audit-implementation-against-design](https://github.com/ViskyG/agent-skills/blob/main/skills/shared/audit-implementation-against-design/SKILL.md) + the shared Waypoint workflow.

These general skills live in a separate repository and may require separate access. [Prepared Waypoint integration amendments](next-stage/skills/conformance/README_RU.md) remain candidates; their presence here does not mean the canonical skills were updated or installed. For project-local use, pass the bundled files explicitly in the relevant task context.

## Try the demo

Requirements: **Python 3.10+** and a browser. Local installation and Codex observation have been verified on **Linux**. Running the app requires no Node.js or frontend build step.

```bash
git clone https://github.com/ViskyG/Waypoint.git
cd Waypoint/waypoint
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m waypoint --data ../.runtime/demo serve --demo --port 8770
```

Open the local read-only URL printed by the service. Keep its access key private.

The demo uses fictional tasks and agents, its own data directory, and port `8770`. It needs no Codex connection. Stop this foreground service with `Ctrl+C`; restarting with the same data directory retains its state.

For a preview without installation, download the repository and open [waypoint/preview.html](waypoint/preview.html) in a browser. It is a self-contained fictional demonstration. [roadmap/PREVIEW.html](roadmap/PREVIEW.html) is a separate offline snapshot of Waypoint's own roadmap structure.

## Connect Codex

Use a separate data directory for real work. From `waypoint/`, with the virtual environment active, start the local service:

```bash
python -m waypoint --data ../.runtime/local serve --port 8769
```

In another terminal, from the same directory and virtual environment, import your roadmap and start observing an existing session:

```bash
python -m waypoint --data ../.runtime/local --project my-project \
  plan-import /path/to/project.plan.json --request-id initial-plan-v1

python -m waypoint --data ../.runtime/local --project my-project observe \
  --thread REAL_NATIVE_THREAD_ID \
  --ipc /absolute/path/to/ipc.sock \
  --rollouts /absolute/path/to/codex/sessions
```

Replace the example paths and native thread ID with your actual local values. The plan's `project_id` must match `--project`. Use the [roadmap template](roadmap/templates/PROJECT.plan.json) as a starting point and replace its sample requirements and project ID.

The observer reads the selected session and its verified descendants through local IPC and saved JSONL records. The IPC socket must belong to the same user. Compatibility depends on the installed Codex client and its internal formats.

To attach future observations to tasks, each executor creates its own verified binding and declares its scope with `focus`. Parentage alone does not assign a subagent's work to a task. The [shared workflow](next-stage/skills/conformance/WAYPOINT_WORKFLOW.md) documents binding, scope, result recording, and safe roadmap updates. The [local operation guide](waypoint/LOCAL_RUN_RU.md) covers startup, backup, and recovery; these detailed guides are currently in Russian.

## Local data and architecture

```text
Roadmap JSON + explicit executor signals
                    ↓
Existing Codex → local observer → SQLite journal → local HTTP → browser
```

Python/FastAPI serves the API and static HTML, CSS, and JavaScript. The journal stores plan versions and accepted events; the browser uses bounded message windows and paged evidence histories. Waypoint's observer does not send conversations to a model or add a model heartbeat.

Runtime databases, access keys, bindings, and source logs are private installation state. Keep them outside Git; `.runtime/` is ignored. The service binds to loopback and is intended for local, single-user operation. Public multi-user hosting is outside the verified scope.

## Status and verification

Current application version: **0.2.0**. The implemented scope includes roadmap editing and versioning, observation, agent hierarchy, reading filters, result evidence, algorithm history, and the bilingual interface. A third visual theme awaits a confirmed design reference.

The latest recorded unit/contract/API run passed **142 tests**. Browser checks cover the bilingual UI, reader state, the installed local service, and offline previews. Real Codex observation and restart recovery have separate recorded evidence:

- [Current bilingual UI acceptance and limitations](next-stage/evidence/i18n-20261020/REPORT_RU.md)
- [Functional acceptance and remaining limitations](next-stage/evidence/remaining-20261020/FINAL_RU.md)
- [Recorded live Codex check after restart](next-stage/evidence/remaining-20261020/LIVE.json)

Synthetic fixtures demonstrate only their stated scenarios; they are not evidence of a real Codex connection. Historical reports describe the source and environment of their recorded runs.

To run the Python checks, from `waypoint/`:

```bash
python -m pip install -e '.[test]'
python -m pytest -q
```

Chromium scenarios are in `waypoint/tests/` and require `.[browser]` plus the Playwright browser installation. Live observation checks additionally require your local Codex session.

## Documentation

| Guide | Purpose |
|---|---|
| [Local operation](waypoint/LOCAL_RUN_RU.md) | Service, observer, private data, backup, and recovery |
| [Development entry point](START_HERE_RU.md) | Current project state and acceptance references |
| [Roadmap](roadmap/ROADMAP.md) / [JSON](roadmap/ROADMAP.plan.json) | Work structure and planned criteria; runtime status lives in the journal |
| [Architecture](waypoint/design/ARCHITECTURE.md) / [contracts](waypoint/design/CONTRACTS.md) | System structure and data formats |
| [Shared roadmap workflow](next-stage/skills/conformance/WAYPOINT_WORKFLOW.md) | Instructions for designers, executors, and auditors |
| [Project skills](waypoint/skills/INTEGRATION.md) | Bundled map/observation instructions and their publication/installation status |
| [Publication preparation](docs/PUBLICATION_RU.md) | Repository preparation, audit scope, and pending owner decisions |

Most detailed engineering documents are in Russian. Existing assignments, reports, and historical IDs are preserved in the repository.

## License

A public license has not yet been selected. This repository does not currently include a `LICENSE` file. Third-party dependencies retain their respective licenses.
