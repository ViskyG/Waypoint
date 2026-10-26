---
name: waypoint-map
description: "Create or revise the user's Waypoint work map as part of an authorized design/roadmap task; preserve requirements, acceptance, identity and cheap executor context."
metadata:
  version: "0.3.1"
  status: "draft-candidate"
---

# Author a Waypoint map

Use the approved project context and `schemas/plan.schema.json` in the owning Waypoint package. This candidate is not installed or registered in the global library. It does not start work or grant permissions.

When creating/adopting a project map, use the project's `.project/passport.json`
when available for its human name and verified identity. For a new identity,
follow the [shared project-passport skill](https://github.com/ViskyG/agent-skills/blob/main/skills/shared/project-passport/SKILL.md)
once. Keep the existing `waypoint.plan/1` `project_id` stable; if different
from passport `id`, record the verified mapping in `bindings.waypoint`.
Do not derive names from Runner IDs, rewrite historical map/task IDs, or treat
the passport as proof that the installed Waypoint imports it. Routine map
revisions do not require loading the passport skill.

Create one dependency graph, not a second roadmap alongside the existing plan. Each meaningful block needs a stable readable ID, title, assignment, acceptance criteria keyed by ID, relevant planned tests and source references. Choose coherent work units rather than one block per function or file. A block may contain another graph. Parentage and dependency edges are explicit; horizontal expansion and vertical refinement are layout hints. Preserve existing positions when adding work. Do not resize/replan on each incoming message.

For an update, obtain the current plan/base version once at the useful boundary. Preserve IDs for unchanged work; new work gets new IDs. Change only intended requirements or dependencies. Export the proposed snapshot with its base_version and one request_id; local `wp plan-import --merge` can reconcile disjoint fields. A conflict is a concrete difference to resolve, not permission to overwrite another executor's work. Retry the same request with identical contents after an uncertain delivery.

The map follows the work: do not add mandatory approval, status transitions, exclusive claims, test gates or restrictions on delegation. Keep assignments on the left and expected/actual acceptance differences on the right. A status says what the executor reported, not what the UI permits.

Give an executor only `wp --project PROJECT packet NODE` and exact source/contracts needed for that work. Keep explanations reachable, not repeatedly loaded. A chat without local access returns one bounded snapshot/change package; it must not claim the local map was updated.

## Observability profile 1
Use the owning project's `waypoint.observability/1` contract when supported. Author
node.x_observability.intent for the human Task/Plan views; keep assignment as the
technical executor contract. An old viewer retaining these fields does not prove
it can display them. New typed requires edges declare output, phase, target scope
and availability basis; order edges do not gate work. Use one effective resolver
for inherited conditions, not UI geometry or a second local algorithm.

Curate project-level algorithm definitions with block refs only for significant
custom logic. Link implementation and testability; keep actual evaluations in events.
Preserve every old ID, assignment, event and unknown extension when migrating from
a current base. Missing readable intent is visible missing data, not a runtime LLM
summary. The owner's three selected theme requirement is not reduced by a missing
reference. Chat capsules remain optional; project/Plan views add no agent reporting.

## Scenario-based handoff and evidence identity
Use [the project workflow](../../../next-stage/skills/conformance/WAYPOINT_WORKFLOW.md)
when authoring or revising packets. Keep one graph, stable IDs, readable intent and a
separate technical assignment. Map acceptance/test IDs to user scenarios, relevant
negative cases, sufficient evidence level and invalidation conditions. Source review,
unit checks, synthetic HTTP/browser and real native-source integration establish
different claims. Planned test definitions are not executed passing results.

Name real prerequisite outputs/revisions, workspace and start/finish phase; keep
preferred order and containment distinct. Status done is not input availability.
Require immutable/versioned artifact references in the handoff, preserving earlier
reports instead of overwriting their paths. Record unavailable historical proof as
unknown. Explain partial completion and linked fixes rather than making a whole
product green from a criterion total.

Tell each executor and child to validate its own binding, focus before work, register
actual criterion outcomes before completion and release scope at handoff. This is
trace discipline, not an exclusive claim, new approval gate or instruction to send
agent-control commands. Project and global skill publication/installation remain
separate from preparing this draft.
