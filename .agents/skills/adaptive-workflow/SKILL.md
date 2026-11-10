---
name: adaptive-workflow
description: "Automatically select and sequence the smallest useful set of installed development skills from a natural-language software task. Use when no workflow was named or several skills may apply."
---

# Adaptive Workflow

Turn an ordinary software request into a small, ordered workflow. Users should be
able to describe the problem or outcome without knowing any skill name. Explicit
user choices, requested scope, and repository instructions always take precedence.

## Understand the outcome

Identify the requested outcome before selecting a workflow: explain, diagnose,
implement, review, plan, verify, or assess a release. Preserve boundaries such as
"diagnose only", "planning only", or "do not edit". Do not treat workflow selection
as permission for a broader action.

Keep `adaptive-workflow` as the primary route when the request gives neither an
identifiable target nor an observed symptom, for example “fix the system”. Ask one
question that exposes the target or actual-versus-expected behaviour; do not guess a
debugging target merely because the request contains the word “fix”.

Inspect the available skill names and descriptions. Choose one primary workflow and
no more than two supporting workflows unless a longer sequence is demonstrably
necessary. Read the complete `SKILL.md` for every selected workflow before following
it; do not load every skill as a precaution.

## Decide whether to ask

Use confidence and consequence, not a keyword count:

- **Clear task:** briefly announce the selected workflow in plain language and
  continue. Do not ask the user to approve an internal skill choice.
- **Several materially different outcomes:** show two or three outcome-based choices,
  put the recommended option first, explain each in one sentence, and wait for the
  user's choice. Prefer labels such as **Diagnose only** or **Fix and verify**, not
  internal skill names.
- **Missing information blocks safe progress:** ask one concise question. Continue
  read-only inspection when it remains useful.

The user may replace the route at any time. A named skill is an explicit override;
combine it with another skill only when needed to complete the requested outcome.

## Compose the workflow

Use these routes as defaults, then adapt to the actual repository and request:

| User outcome | Primary workflow | Optional support |
| --- | --- | --- |
| Implement a clear change or review code | `lean-senior-engineering` | `verification-before-completion` after a change |
| Define UI direction or enterprise data behavior | `ui-design-intelligence` | `feature-discovery` when product outcomes are unresolved |
| Resolve ambiguous domain terms, states, or invariants | `domain-modeling` | `feature-discovery` for unresolved product choices; specification verification after implementation |
| Trace requirements to implementation evidence | `spec-to-code-verification` | `systematic-debugging` only for an unexplained failure |
| Review a third-party skill before adoption | `skill-security-guard` | none; adoption needs explicit user authorization |
| Protect money, ledger, retry, or batch integrity | `transaction-safe-engineering` | `spec-to-code-verification` for requirement evidence; no default loading |
| Exercise user journeys in a browser | `browser-journey-testing` | `browser-diagnostics` for an unexplained failure; `ui-quality-verification` for a broader audit |
| Implement an agreed interface | `ui-implementation` | `ui-quality-verification` after a material UI change |
| Audit an existing interface visually and interactively | `ui-quality-verification` | `browser-diagnostics` only for an unexplained failure |
| Diagnose or fix an unexplained failure | `systematic-debugging` | `verification-before-completion` after a fix |
| Reproduce a browser-visible failure | `browser-diagnostics` | `systematic-debugging`, then verification after a fix; use `ui-quality-verification` only for a separate planned audit |
| Clarify a feature whose choices change the result | `feature-discovery` | implementation and verification only when requested |
| Complete a substantial multi-module or multi-session change | `research-plan-implement` | phase plan with explicit skills and verification |
| Explain architecture, data flow, or impact | `architecture-map` | none unless the user separately requests a change |
| Assess a release candidate | `release-readiness` | focused verification when evidence is missing |
| Verify an existing change | `verification-before-completion` | none by default |

Do not add `verification-before-completion` to a read-only explanation merely to
make the route look complete. Do not add implementation to diagnosis or planning
unless the user requested it.

Avoid redundant workflow chains. `systematic-debugging` already owns an authorized
focused fix after it locates the cause, so do not add `lean-senior-engineering` merely
because the investigation may end with a code change. Add a supporting workflow only
for a separate responsibility the primary workflow does not cover.

## Phase orchestration

A substantial implementation can change skill at phase boundaries without reloading the
whole skill pack or asking after each phase. Use one agent as the orchestrator:

1. Route the task to a planning skill, normally `research-plan-implement`.
2. Require a phase plan with one primary skill, optional support, entry/exit evidence, and
   dependencies. The per-phase limit is one primary plus at most two support skills.
3. At each boundary, verify the predecessor's exit evidence, append a skill trace, load
   the next `SKILL.md`, announce the phase briefly, and continue.
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

Record a compact trace:

```json
[
  {"phase": "plan", "skill": "research-plan-implement", "status": "completed", "evidence": "plan.md"},
  {"phase": "backend", "skill": "lean-senior-engineering", "status": "completed", "evidence": "backend tests"},
  {"phase": "ui", "skill": "ui-implementation", "status": "completed", "evidence": "interaction checks"}
]
```

## Announce and continue

For an automatic route, use one short update such as:

> I’ll reproduce the failure, trace its cause, make the smallest authorized fix, and
> rerun the original checks.

Then continue working. Keep internal routing details out of the final answer unless
they help explain the evidence or a limitation.

For an interactive route, make the decision easy for someone who has never heard of
the skills. For example:

1. **Fix and verify (recommended)** — reproduce the problem, repair it, and check the
   original scenario.
2. **Diagnose only** — identify the cause without changing source files.
3. **Plan a broader redesign** — inspect the current flow and define acceptance
   criteria before implementation.

Ask only when these outcomes would lead to meaningfully different work.

## Keep the interaction natural

Match the user's language and use ordinary product or engineering terms rather than
making the user operate the skill system. Lead with the next useful action, not
generic praise. A clear request does not need “Would you like me to continue?”

Sound like an approachable friend helping at the same desk, not a ticketing system or
formal consultant. Match a casual register when the user uses one, without forced
slang or fake emotion. Welcome basic questions and half-formed ideas: explain the
missing context kindly, then help shape the next step. Use “we” or “kita” naturally
when it reflects shared problem-solving, but do not manufacture familiarity.

When the user's proposed method creates a concrete safety, privacy, data-integrity,
financial, or recovery risk, say so plainly and recommend a safer route. Do not agree
for politeness and do not become argumentative. State uncertainty and unavailable
evidence honestly. Never imply that a remembered fact, tool result, or completed test
exists when the current runtime has not provided it.

## Finish with evidence

Close with the phase trace, not only a success sentence:

| Phase | Skill | Support | Evidence |
| --- | --- | --- | --- |
| plan | `research-plan-implement` | — | plan and acceptance criteria |
| backend | `lean-senior-engineering` | — | test result |
| ui | `ui-implementation` | — | interaction result |
| ui-audit | `ui-quality-verification` | — | screenshots and keyboard result |
| final | `verification-before-completion` | — | final checks and gaps |

Report skipped phases, blocked checks, and remaining uncertainty. Do not list a skill
that was not actually loaded or used. Do not ask whether to continue an already-authorized
next phase after the work is complete.
