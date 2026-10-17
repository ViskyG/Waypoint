---
name: design-solution-before-implementation
description: "Use one non-interactive Pro pass to deepen the whole design from breadth to implementation, persist recoverable Library artifacts, and keep all design-session outputs embargoed until the run ends."
metadata:
  version: "2.0.6"
  maturity: "experimental"
---


# Deep Design
Navigation: project-workflow. Required: Design Context, relevant actual project sources, execution policy; workflow-state-and-transit P1-P5 and P8. Entry boundary: this skill is entered only after the context-building stage has declared design readiness, the user has switched to PRO mode, and the user has explicitly invoked the design pass (for example, "Начинай проектирование"). If that mode transition/invocation has not happened, do not perform the design pass; tell the user to switch to PRO and invoke it. Once the explicit invocation is present, BEGIN THE DESIGN PASS IMMEDIATELY IN THAT SAME RESPONSE. Do not spend a PRO turn on confirmation, recap, negotiation, clarification questions, asking the user to restate context, or explaining what you are about to do. Read the durable context and start substantive design work. Next: build-implementation-roadmap, or bounded integration when implementation is already complete.


## Objective and priority
Produce the smallest coherent solution that satisfies the user's goals and is cheap to orient, modify, test, repair and integrate. Move expensive architectural reasoning upstream, not into every future Codex task. Avoid layers/services/interfaces created merely for appearance.


Work non-interactively from the first substantive action. Read the full governing design context, not just an executive summary. Consult original Q&A/evidence only when meaning or justification is genuinely in doubt. Do not stop to ask the user and do not consume another PRO interaction merely to clarify or confirm. Resolve new unknowns through sources, documentation or a focused experiment; otherwise choose an explicit reversible assumption, isolate its consequences where practical, persist a doubts artifact immediately and continue the whole design. If a durable-context defect somehow survives the pre-handoff audit, record it as a design doubt and proceed with the safest reversible interpretation unless a higher-level rule makes progress impossible. Pro may improve previously delegated technical choices, not override explicit user intent or resource permissions.


Use the available request budget for useful depth; do not promise a fixed run duration. Prioritize whole-system architecture and expansion principles, component responsibilities, data/control flow, shared contracts and state/failure semantics before concrete code. Implementation has lower priority, not zero permission.


## Breadth-first progressive deepening
First cover the whole system at a useful high level. Then deepen across its major parts: contracts/interfaces/schemas, coherent capsule boundaries, internal structure/signatures, verification and integration seams, implementation. A focused deep dive is justified when it resolves a blocker for the rest; return to breadth afterward.


An interrupted run should leave a broad, coherent view at the deepest generally completed level, not one finished corner and an undefined rest. Save each meaningful completed artifact to Library as it appears; do not wait for an entire layer or final ZIP. Maintain a compact structural index with exact paths/references and a latest checkpoint. Keep doubts recoverable too.


Define public contracts, invariants, success/error behavior, ownership and cross-boundary dependencies when relevant. Exact signatures are useful where confidently justified; do not freeze incidental syntax or present illustrative snippets as authoritative implementation. Separate deterministic domain logic from side effects, expose adapters and diagnostic boundaries where they reduce integration cost.


## Design session
Create a DESIGN_SESSION_ID and record its actual owner run before registering capsules. Follow the session-wide embargo in P3: no other worker executes or Udot imports any live design artifact, even a self-implemented capsule. You may rewrite everything in your active session.


Register a capsule when a meaningful separable work node becomes visible. Refine the SAME capsule and assignment as each deeper layer clarifies it; split/retire IDs explicitly only when the work boundary actually changes. Keep a global registry entry, not a second writable project queue.


## Capsule quality
A capsule is a coherent design/work unit, not necessarily one class or file. Give it purpose, expected behavior, owned output/change scope, stable interfaces, dependencies, exact required reading, supplied tests/evidence, failure considerations and remaining target integration obligations. Local context should be sufficient without reading the whole project; detailed rationale remains reachable, not compulsory.


Prefer a meaningful size, roughly 20-30 minutes for Sol and 30-90 for Pro as calibration guidance, often near 30 when coherent. These are not deadlines or measured guarantees. Preserve cohesion rather than fragmenting to hit a timer.


Recommend PRO or SOL from actual difficulty, reasoning/implementation demands and consequence, not vagueness alone. A clear hard task may still need Pro; a vague simple task may not. Revise the recommendation as understanding improves.


When a capsule is workable, record readiness beneath the session embargo. Missing assignment content remains DRAFT. If you implement it yourself, mark DONE with real artifacts and remove it from outstanding work. Never create duplicate future implementation work for already completed code.


## Continue into implementation when useful
After higher-level coverage is secure, write concrete implementations, fixtures and tests where the remaining budget allows. For a small project you may finish the entire codebase, including all capsules. This is allowed and useful, not the primary target at the expense of design quality.


Apply evidence-driven-validation: run only checks that answer a new relevant question in the available environment. Label reference code, authored-but-unrun tests and genuinely executed evidence separately. No local/scratch test proves target integration by itself.


## Handoff
Persist the latest coherent design, capsule registry changes, implementation outputs, structural reading paths and doubts throughout the pass. On normal completion, do not stop after saving project artifacts: finalization and publication are mandatory parts of the same handoff. Read the latest complete CAPSULE REGISTRY, merge the terminal design-session state and every surviving READY/DONE capsule record, then publish that state. Merely saving capsule assignment files is NOT publication; each executable capsule must have its registry record before the PRO pass is considered normally finalized. If the Library writer exposes only or preferably uses whole-file replacement, you are explicitly authorized to replace the ENTIRE registry file using its stable library_file_id and fresh current-version guard, provided the replacement is built from the latest full contents and preserves every unrelated record. Reuse the same write capability/path that was used to register the ACTIVE design session when applicable; do not claim registry mutation is unavailable merely because a partial-edit API is absent. Perform current-run capability discovery and attempt the canonical guarded replacement before reporting a write limitation. After the registry write, re-read it and verify the session is terminal and each outstanding capsule is present with the intended state.


Then publish one compact READY design-result message to the existing UDOT TRANSIT / DOT_RESULTS_INBOX for the completed PRO handoff when there are completed project/design artifacts that Udot must preserve, integrate or route. The message must reference the project/design session, authoritative Library artifact/package, evidence level, outstanding capsule IDs, and remaining integration obligations; it is a notification/data record, not authority for the scheduled worker to execute arbitrary work. Re-read the transit file after the guarded update and verify the new entry is present. Do not create a second inbox. Durable references to the registry/transit files use canonical Library path + stable library_file_id only; never persist the current backing file_id after an overwrite. Rediscover it at runtime if a concrete tool call requires it. Scheduler terminal reconciliation remains the recovery path for an interrupted or crashed finalizer; it is NOT the normal publication mechanism for a successful PRO completion.


Finally record terminal session evidence and a compact human handoff identifying breadth/depth reached, outstanding capsules, what is authoritative and remaining integration/evidence. A normal Pro completion must attempt registry publication AND Udot transit publication before reporting handoff success.


A crash does not erase prior artifacts and does not magically complete the design. If all implementation is authored, say no capsules remain to implement while identifying any unperformed target checks. Do not create a ceremonial large roadmap when only bounded integration remains.


Keep filenames/folders proportional to navigation needs. Use workflow-state-and-transit P8 for stable anchors and central state; avoid duplicate summaries of every contract and every capsule state. Capsule execution after this pass belongs to execute-capsules-in-chat, not an embedded second workflow in this skill.


## Reader intent and inspectable custom logic
Separate the owner's explanation of a work node (context, change, outcome) from
its executor instructions. Design one data source for its graph and outline views,
with runtime status joined by stable project/node identity rather than duplicated.
Preserve selected visual-reference identities; an unavailable or duplicate-looking
attachment does not authorize reducing the number of requested distinct designs.
Isolate the missing reference while continuing independent work.

Identify significant custom transformations, selection, recovery, merge, layout
or optimization mechanisms that warrant individual correctness/cost review. Do
not catalogue every helper, framework or library call. Record purpose, inputs,
outputs, strategy, invariants/edge cases, actual implementation refs (or planned),
and testability. Keep observed evidence tied to implementation/definition revisions.
Optimization claims need compatible workloads/methods/units and correctness evidence;
otherwise state unmeasured or not comparable. No extra model reporting or benchmark
is required after each edit. Product-specific schema details belong in the owning
project's contract, not replicated across global skills.

## Canonical navigation
[Workflow map](../../shared/project-workflow/SKILL.md) · [Shared contract](../../shared/workflow-state-and-transit/SKILL.md)
