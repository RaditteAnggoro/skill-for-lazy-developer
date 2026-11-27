# Phase orchestration

Load this reference only for a substantial implementation that changes skill at phase
boundaries. A single-phase task does not need it.

A substantial implementation can change skill at phase boundaries without reloading the
whole skill pack or asking after each phase. Use one agent as the orchestrator:

1. Route the task to a planning skill, normally `research-plan-implement`.
2. Require a phase plan with one primary skill, optional support, entry/exit evidence, and
   dependencies. The per-phase limit is one primary plus at most two support skills.
3. At each boundary, verify the predecessor's exit evidence, append a skill trace, update
   the handoff record (below), load the next `SKILL.md`, announce the phase briefly, and
   continue.
4. Use the planned next skill instead of asking “should I continue?” when the work remains
   inside the authorized scope.
5. Re-route only when new evidence changes the plan. Ask once only when the next phase
   changes product scope, external effects, or a safety/data/financial decision.

Typical mixed backend/UI sequence:

```text
research-plan-implement       plan and acceptance criteria
lean-senior-engineering       backend and contract tests
ui-design-intelligence        only if the UI direction is unresolved
ui-implementation             UI using the frozen contract
browser-journey-testing       exercise affected user journeys in a real browser
ui-quality-verification       visual, responsive, keyboard, and state checks
spec-to-code-verification     requirement-to-evidence matrix
verification-before-completion final checks and residual gaps
```

Do not load every skill up front. Load each selected skill when its phase starts. Do not
start a dependent UI phase before the backend contract is frozen; sequential orchestration
is the default when phases share files, contracts, or data. Use parallel work only for
genuinely independent, disjoint ownership.

For substantial UI work, schedule the requested or needed browser journey and quality
audit as subsequent phases, followed by verification. Do not omit a required check merely
to fit every activity into one phase's support list. A small UI edit still gets focused
verification without a compulsory broad audit.

## Survive long sessions and compaction

Phase IDs such as `p4` must not live only in chat history, because a long session may be
summarized and lose them. For a task with two or more phases, keep the handoff record
from `research-plan-implement` current at every phase boundary, not only before stopping:

- Path: the project's durable planning location, otherwise
  `.agents/artifacts/<task-slug>/handoff.md`.
- Per phase: phase ID, primary skill, status (`pending`, `in_progress`, `completed`,
  `blocked`, `skipped`), and the evidence that closed it.
- Next action: the next phase ID and its primary skill.

Write it before announcing the next phase so a compacted session can resume from the file.

## Resume on a short continue command

When the user sends only a short continue command such as `lanjut`, `gas`, `next`,
`continue`, `go`, or `lanjut p4`, and an active handoff record exists:

1. Read the handoff record and check that the recorded code state still matches.
2. Continue the named phase, or the recorded next phase when none is named, with the
   primary skill recorded for it.
3. Do not re-route the task and do not ask what to continue.

Ask one question only when no active handoff exists, when several active handoffs match,
or when the named phase is missing, already completed, or blocked by an open decision.
A handoff record is a pointer, not proof: recheck the evidence the next phase depends on.

## Trace record

Record a compact trace:

```json
[
  {"phase": "plan", "skill": "research-plan-implement", "status": "completed", "evidence": "plan.md"},
  {"phase": "backend", "skill": "lean-senior-engineering", "status": "completed", "evidence": "backend tests"},
  {"phase": "ui", "skill": "ui-implementation", "status": "completed", "evidence": "interaction checks"}
]
```

For the user-facing phase trace table and when to use it, follow “Finish with evidence”
in the main `SKILL.md`.
