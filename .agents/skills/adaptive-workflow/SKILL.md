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
| Diagnose or fix an unexplained failure | `systematic-debugging` | `verification-before-completion` after a fix |
| Reproduce a browser-visible failure | `browser-diagnostics` | `systematic-debugging`, then verification after a fix |
| Clarify a feature whose choices change the result | `feature-discovery` | implementation and verification only when requested |
| Complete a substantial multi-module or multi-session change | `research-plan-implement` | verification at implementation handoff |
| Explain architecture, data flow, or impact | `architecture-map` | none unless the user separately requests a change |
| Assess a release candidate | `release-readiness` | focused verification when evidence is missing |
| Verify an existing change | `verification-before-completion` | none by default |

Do not add `verification-before-completion` to a read-only explanation merely to
make the route look complete. Do not add implementation to diagnosis or planning
unless the user requested it.

## Announce and continue

For an automatic route, use one short update such as:

> I’ll reproduce the failure with Systematic Debugging, make the smallest authorized
> fix, and use Verification Before Completion to check the original scenario.

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

## Finish with evidence

The selected workflows own their normal output and checks. Report actual results,
blocked checks, and remaining uncertainty. Never claim the router, a skill, or a
mentioned tool was used merely because its name appeared in the task.
