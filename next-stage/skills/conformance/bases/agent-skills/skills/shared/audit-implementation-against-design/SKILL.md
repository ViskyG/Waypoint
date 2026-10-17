---
name: audit-implementation-against-design
description: "Perform a bounded milestone or final conformance audit against accepted intent and actual artifacts/evidence; identify deviations and concrete remediation without perpetual self-audit."
metadata:
  version: "2.0.0"
  maturity: "experimental"
---


# Implementation conformance audit
Navigation: project-workflow. Inputs: accepted context/design, relevant roadmap boundary, actual implementation and evidence. Use evidence-driven-validation and workflow-state-and-transit P5-P8. Next: Udot remediation or completion.


Run when requested, at a planned meaningful milestone or after a concrete architecture/navigation discrepancy. Do not make this audit a mandatory ritual after each packet.


Read the accepted intended behavior and actual affected implementation. Follow exact structural/rationale references only when needed. Passing tests are evidence, not a verdict that every requirement or design contract was implemented.


Compare important user scenarios, boundaries/interfaces/invariants, expected outputs, omission/non-goal constraints, selected resource policy and outstanding integration obligations. Separate deliberate authorized deviations from accidental drift and uncertain/unverified behavior. Audit anchors/state navigation only at a relevant boundary or after an observed broken reference.


Classify a finding by consequence and evidence: demonstrated defect, missing requirement, material design deviation, unverified claim, or optional improvement. Do not label an improvement a failure of an unchanged accepted scope. State exact affected artifact/location, expected versus actual behavior, consequence, and the smallest useful remediation.


For completed capsule defects create/route -FIX / -FIX-2 linked to original evidence. Material central hypothesis or goal changes go to the user; routine local repairs go to the permitted executor. Preserve valid unaffected work and evidence. Do not automatically rerun all tests or redesign everything.


Report what was examined, what evidence supports the conclusion, actual unresolved obligations and the next owner/action. A model-only trace is not an integration pass. Completion cannot be claimed merely because the outstanding capsule queue is empty.


## Canonical navigation
[Workflow map](../project-workflow/SKILL.md) · [Shared contract](../workflow-state-and-transit/SKILL.md)
