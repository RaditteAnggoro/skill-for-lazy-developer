---
name: research-plan-implement
description: "Research and execute a complex change across modules or sessions with a resumable local plan. Use for substantial migrations or multi-stage features, not small fixes."
---

# Research, Plan, Implement

Maintain enough evidence and state to carry substantial work across sessions. Follow the user's current stage: research only, plan only, implement an existing plan, or complete the full change. Do not infer implementation authorization from a request for analysis.

## Locate current state

Read applicable project instructions, the named plan or handoff, and the relevant current code. Check branch and working changes where Git exists. Verify that saved statements still match the files; a prior report is not proof of the current state.

Reuse the project's planning conventions. For authorized implementation or a request for saved planning records, use `.agents/artifacts/<task-slug>/plan.md` and `handoff.md` if no durable location exists. Choose a new slug for unrelated work and preserve existing artifacts. For research-only or plan-only requests without saved documents in scope, return the plan and handoff information in chat. Do not create these files for a short fix.

## Research and plan

Trace affected components, public contracts, persistence, and integration boundaries. Record code locations, facts, assumptions, unresolved decisions, and the smallest coherent design. Avoid a full repository survey when only one subsystem matters.
For version-sensitive documentation or complex code exploration, use the shared [tool selection guide](../adaptive-workflow/references/tool-selection.md) when a specialized capability adds evidence.

Break implementation into increments that can be exercised end to end. State each increment's outcome, dependencies, likely files, and verification. Use actual project commands when known; mark unknown commands as unresolved instead of inventing them. Account for compatibility and data migration where needed.

## Phase plan

For a multi-stage implementation, the plan is also the orchestration contract. Write a
compact phase table or YAML block that an agent can execute without re-deciding the
whole route at every step:

```yaml
task: one sentence
authorized_scope: [backend, ui, verification]
phases:
  - id: plan
    primary: research-plan-implement
    support: []
    entry: request is understood
    exit: phase plan and acceptance criteria recorded
    evidence: plan.md
  - id: backend
    primary: lean-senior-engineering
    support: []
    depends_on: [plan]
    entry: API contract is decided
    exit: backend tests pass
    evidence: test output
  - id: ui
    primary: ui-implementation
    support: []
    depends_on: [backend]
    entry: API contract is frozen
    exit: UI states render and interactions work
    evidence: interaction check
  - id: ui-audit
    primary: ui-quality-verification
    support: []
    depends_on: [ui]
    entry: UI build is available
    exit: visual, responsive, keyboard, and states pass
    evidence: screenshots and interaction results
  - id: spec-audit
    primary: spec-to-code-verification
    support: []
    depends_on: [ui]
    entry: implementation evidence exists
    exit: each requirement is mapped to evidence
    evidence: traceability matrix
  - id: final
    primary: verification-before-completion
    support: []
    depends_on: [ui-audit, spec-audit]
    entry: all implementation phases are complete
    exit: final checks pass and limitations are reported
    evidence: final verification record
```

Rules:

- Give each phase **one primary skill** and at most two supporting skills. The limit is
  per phase, not a reason to load every skill at the start.
- Use stable phase IDs and explicit `depends_on`. Do not start a dependent phase before
  its predecessor's exit criterion is met.
- Record the files or contracts a phase may change. When phases can run concurrently,
  give them disjoint ownership; when they share a contract or files, keep them sequential.
- Freeze an API, schema, or design contract before a phase that consumes it. Do not let a
  later phase silently redefine it.
- Append a skill trace as phases start and finish. A phase is complete only when its
  evidence exists; a green build alone is not phase evidence.
- Re-route only when new evidence changes the plan. Re-route within the authorized scope
  without asking again; ask only when the next phase changes product scope, external
  effects, safety, or a decision that materially changes the result.
- Keep the final verification phase unless the request is explicitly research-only or
  review-only.

## Execute or resume

When implementation is requested, complete ready work within the authorized scope. Use the plan to guide delivery, revising it when code evidence changes a routine technical choice. Surface decisions that change the intended product or external effects. Do not ask to approve each already-authorized step.

Preserve user changes. Keep independent tasks separate if using agents; delegate only when tools are actually available and inspect their output. Do not automatically create branches, worktrees, chats, commits, or external tickets.

## Keep a useful handoff

When saved records are in scope, update the plan and handoff at meaningful milestones or before stopping, using [handoff-template.md](references/handoff-template.md) as a compact shape. Otherwise include the relevant record in chat. Include exact checks and remaining work, not a transcript of the conversation. Keep credentials and private payloads out of artifacts.

On resumption, verify the recorded environment and code state, complete remaining authorized work, and check the original acceptance criteria. A plan file is not completion evidence.

When the final phase closes, report the phase trace rather than a flat “done”. For each
phase, name the primary skill, optional support, outcome, and evidence. Mark skipped
phases and unresolved gaps. Do not list skills that were not actually loaded or used.
