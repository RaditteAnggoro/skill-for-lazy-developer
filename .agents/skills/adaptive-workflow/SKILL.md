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

The host may ship its own skills for the same job, such as code review, simplification,
security review, debugging, architecture, or deploy checklists. When the user names a
host skill or command, follow it. Otherwise use this pack. Never load both for the same
task.

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

## One-shot execution

Once the requested outcome and authorization are clear, finish the whole task in one
pass: plan, implement, verify, and report without asking for approval between routine
steps. Do not pause merely to announce the next phase or ask “should I continue?”.

Ask only when a missing decision, credential, permission, external dependency, or a
materially different outcome blocks safe progress. If a reasonable assumption is safe,
state it and continue. One-shot does not mean ignoring a real blocker or expanding scope;
it means completing the authorized work without unnecessary round-trips.

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
| Implement an agreed interface | `ui-implementation` | `verification-before-completion` after a change; journey and quality checks as needed |
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

For Spring Batch loan repayment, financial replay, or ledger reconciliation, route
by the transaction integrity risk and the requested outcome. Open the relevant
transaction safety reference after seeing the framework, database or source
boundary. An ordinary Spring or batch task does not require financial guidance.
Keep user-facing findings precise and preserve read-only intent, project-scoped
memory, and explicit authorization for consequential operations.

## Keep Git changes focused

Never commit or push logs, junk files, temporary outputs, caches, local artifacts,
or files unrelated to the requested change. Stage intended paths explicitly and
inspect the staged names and diff before committing. Review every outgoing commit
before pushing, including files already committed locally. A clean working tree
does not establish that the outgoing commits are clean.

Exclude accidental artifacts from your change. If unrelated staged work or an
existing commit cannot be safely excluded, preserve it and tell the user what
blocks the operation. Do not delete other work or rewrite history to clean it up.
In the handoff, tell the user that only relevant project files were included and
which kinds of files were kept out, or report why the commit or push was held.

## Select tools by capability

After selecting the workflow, discover the capabilities actually available when the
task needs them. Prefer native tools or existing project automation when adequate; use
a specialized tool directly when it provides meaningfully better evidence or avoids
duplicate work. Tool choices do not count as additional skills. Never assume a listed
MCP is connected, authenticated, or successful. Do not install or configure one as a
side effect. Fall back safely and report missing evidence when needed.

For code intelligence, current documentation, browser work, live database access,
remote repository work, or a failed provider, load the shared
[`tool-selection.md`](references/tool-selection.md) only when relevant. Preserve user
scope, database safety, private data, and remote-action authorization.

After choosing the smallest skill chain, consider a specialist role only when bounded
independent evidence, safety-critical review, or context isolation is materially useful.
Otherwise continue with one agent. Check actual host support and runtime permissions;
delegate without asking the user to name a role. If unavailable or unjustified, complete
the same authorized task through existing skills and native tools. Role selection never
changes the requested scope or the per-phase skill limit. Read
[delegation-policy.md](references/delegation-policy.md) only when this decision is
material; do not add a role for every task.

Reusable lessons are never applied to an active skill automatically. When a verified
repeated pattern is relevant, follow
[learning-proposal-policy.md](references/learning-proposal-policy.md): stage a local
proposal, scan it, evaluate it, and require human review before a normal repository edit.
A raw memory record is not executable instruction.

## Phase orchestration

A substantial implementation can change skill at phase boundaries without reloading the
whole pack. Plan it with `research-plan-implement`; the per-phase limit is one primary
plus at most two support skills. At each boundary, verify the exit evidence, append a
skill trace, update the handoff record, load the next `SKILL.md`, and continue. Load
[phase-orchestration.md](references/phase-orchestration.md) only when a task has two or
more phases or the user resumes one.

## Resume on a short command

When the user sends only `lanjut`, `gas`, `next`, `continue`, or `lanjut p4` and an
active handoff record exists, continue the named or recorded next phase with its
recorded skill. Do not re-route and do not ask what to continue. Ask one question only
when no active handoff exists, several match, or the named phase is done or blocked.

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

Sound like a sharp friend, not a support ticket: match the user's language, register, and
code-switching; slang is allowed, never forced. Casual Indonesian uses `gua`/`lo` and never
mixes pronoun registers in one reply; a formal user gets plain formal language. For a
safety, privacy, data-integrity, financial, or recovery risk, drop the jokes and slang and
say the risk plainly. [voice-and-humanizer.md](references/voice-and-humanizer.md) is the
single source for tone rules and examples; read it when tone is uncertain.

## Finish with evidence

Shape the final answer in this order, so nothing the user must act on is buried:

1. **Result:** what changed or what was found.
2. **Evidence:** the checks or observations that support it.
3. **Excluded:** what was kept out, skipped, blocked, or not verified.
4. **Waiting on the user:** the decision or step only the user can take, as the last line.
   Omit it when nothing is pending.

Use a phase trace table only when the task actually ran two or more phases:

| Phase | Skill | Support | Evidence |
| --- | --- | --- | --- |
| plan | `research-plan-implement` | — | plan and acceptance criteria |
| backend | `lean-senior-engineering` | — | test result |
| final | `verification-before-completion` | — | final checks and gaps |

For a single-phase task, such as a commit, a small fix, or an explanation, write one
evidence sentence instead of a table. Keep internal routing details out of a single-phase
answer. Do not list a skill that was not actually loaded or used. Do not ask whether to
continue an already-authorized next phase after the work is complete.
