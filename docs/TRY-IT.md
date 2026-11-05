# Try automatic workflows in Codex

Run the following prompts from your repository. Replace bracketed input with a real
file, route, command, or task. The examples deliberately use ordinary language: the
adaptive router should announce and load the relevant workflow without requiring a
skill name.

## Confirm discovery

```text
List the repo-local skills under .agents/skills. Show each name and
when you would select it. Do not edit files.
```

Expect sixteen names: the adaptive router and fifteen focused workflows. If the selector
omits them, check the location, hidden folder, and YAML frontmatter, then restart
Codex. If a name collides with another installed skill, inspect both paths and keep
one intended active copy.

## Confirm automatic routing

```text
The checkout page becomes blank after a browser refresh. Reproduce it, fix the
cause, and check the original flow.
```

Expect a brief announcement that combines browser evidence, root-cause debugging,
and verification. The work should continue without asking the user to approve those
internal workflow choices.

Then try an intentionally ambiguous request:

```text
Improve the login experience.
```

Expect two or three outcome-based options, with a recommended choice first. A useful
menu might distinguish a visual improvement, a bug investigation, and a broader flow
redesign. It should not ask a non-technical user to choose between internal skill names.

## Implement a small feature

```text
Add [small feature]. Follow the existing implementation patterns, keep the change
focused, and finish the relevant checks.
```

Expect reuse of existing helpers, a focused diff, and checks matched to the changed behaviour. It should not generate a whole architecture or new framework for a small feature. You can request `lite`, `ultra`, or `off` in plain language; this is a conversational preference rather than a persistent plugin setting.

## Diagnose without implementing

```text
Diagnose why [scenario] fails and explain the supported cause. Do not implement a
fix or change source files.
```

Expect an evidence-backed cause, unresolved uncertainty where appropriate, and a fix direction. Source code should remain unchanged. Temporary diagnostics should respect the requested inspection scope.

## Fix a real regression

```text
[Bug] fails when I run [command], with this output: [output]. Reproduce it, fix the
cause, add an appropriate regression check, and verify the original case before the
handoff.
```

Expect the failure established before the fix when the environment permits, an explanation tied to source, and the original case checked afterwards. Missing dependencies should be reported as a verification gap.

## Review or inventory debt

```text
Review my uncommitted changes. Prioritize concrete defects and regressions. Do not
implement changes.
```

```text
Inventory shortcut comments and important technical debt in [subsystem]. Inspect the
surrounding code, prioritize by impact, and return a ledger without modifying files.
```

Expect locations and triggers, not generic best-practice complaints. A debt ledger should not invent due dates, owners, or previous acceptance.

## Clarify a feature

```text
Plan a CSV import preview for this app. Inspect the existing import flow, ask only
questions that would change the result, and produce acceptance criteria. Planning
only.
```

Expect questions tied to implementation decisions and a small useful scope. A clear button-label change should bypass this workflow and be handled directly.

## Trace data processing

```text
Trace [endpoint or UI action] from input through validation and transformation to
storage and response. Show a diagram, important field mappings, and source evidence.
Do not refactor the implementation.
```

Expect a diagram tied to real files and labelled unknowns. Static code inspection should not be presented as observed runtime execution.

## Complete substantial work

```text
Add [multi-module feature]. Research the affected code, maintain a local plan and
handoff so the work can continue across sessions, then implement and verify the
requested behaviour.
```

To resume in another chat after opening the same repository:

```text
Resume the unfinished work described in `.agents/artifacts/[task-slug]/handoff.md`.
Verify the current code state before completing the remaining tasks.
```

Expect a compact record of decisions, completed work, evidence, and next actions. The handoff does not automatically transfer chat history.

## Assess a release

```text
Assess the current uncommitted changes for our staging release. Inspect existing
scripts and CI, run safe relevant local checks, and report blockers. Do not deploy.
```

Expect a scoped readiness verdict and disclosed checks, not an assumed green pipeline. Production or staging mutations are separate actions.

## Investigate a UI

```text
Diagnose [UI issue] at [development URL]. Inspect the relevant interaction, console,
and network evidence. Use available browser tooling and report anything you cannot
verify. Diagnosis only.
```

Expect actual browser evidence if tools are available, or an honest source-based diagnosis and reproduction checklist if not. A Markdown file cannot install Chrome DevTools MCP or grant access to a browser.

## Compare the result

Choose a small representative change and use equivalent starting code in separate disposable copies if you want a comparison. Do not reset a working repository to create a baseline.

Compare correct behaviour, verification coverage, unrelated edits, unnecessary dependencies, human corrections, and elapsed effort. Smaller diffs only help when the behaviour is complete. These skills do not collect telemetry or calculate a savings score.

Watch for routing failures too: asking the user to choose internal skill names,
requesting workflow approval for an obvious task, loading every workflow, or turning
diagnosis into an unauthorized fix. Other failure signs include an interview for a
trivial task, a whole-repository scan for one-line work, speculative review findings,
repeated tests with no changed evidence, or a completion claim without a result. Keep
observations concrete and revise the router, description, or relevant workflow rather
than adding broad rules to every file.
