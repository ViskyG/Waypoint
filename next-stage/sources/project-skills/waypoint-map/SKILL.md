---
name: waypoint-map
description: "Create or revise the user's Waypoint work map as part of an authorized design/roadmap task; preserve requirements, acceptance, identity and cheap executor context."
metadata:
  version: "0.1.0"
  status: "draft-candidate"
---

# Author a Waypoint map

Use the approved project context and `schemas/plan.schema.json` in the owning Waypoint package. This candidate is not installed or registered in the global library. It does not start work or grant permissions.

Create one dependency graph, not a second roadmap alongside the existing plan. Each meaningful block needs a stable readable ID, title, assignment, acceptance criteria keyed by ID, relevant planned tests and source references. Choose coherent work units rather than one block per function or file. A block may contain another graph. Parentage and dependency edges are explicit; horizontal expansion and vertical refinement are layout hints. Preserve existing positions when adding work. Do not resize/replan on each incoming message.

For an update, obtain the current plan/base version once at the useful boundary. Preserve IDs for unchanged work; new work gets new IDs. Change only intended requirements or dependencies. Export the proposed snapshot with its base_version and one request_id; local `wp plan-import --merge` can reconcile disjoint fields. A conflict is a concrete difference to resolve, not permission to overwrite another executor's work. Retry the same request with identical contents after an uncertain delivery.

The map follows the work: do not add mandatory approval, status transitions, exclusive claims, test gates or restrictions on delegation. Keep assignments on the left and expected/actual acceptance differences on the right. A status says what the executor reported, not what the UI permits.

Give an executor only `wp --project PROJECT packet NODE` and exact source/contracts needed for that work. Keep explanations reachable, not repeatedly loaded. A chat without local access returns one bounded snapshot/change package; it must not claim the local map was updated.
