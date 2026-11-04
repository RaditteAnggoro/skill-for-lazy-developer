# Skills for Lazy Developer
<!-- Author: Raditte Anggoro | Provenance: RA.CODEXSKILLS.2026.10 | Metadata: docs/provenance.json -->

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Workflows](https://img.shields.io/badge/adaptive%20router%20%2B%20skills-9-6C5CE7)](#skills)
[![Maintenance](https://img.shields.io/badge/maintenance-Python%203.9%2B-3776AB?logo=python&logoColor=white)](#development)

**Describe the task. The right workflow finds you.**

An adaptive router and eight focused Codex engineering skills for debugging,
implementation, architecture, browser diagnostics, planning, release review, and
evidence-backed verification. Write a normal software request; the router selects one
workflow or a small ordered combination.

**Best for:** developers who want useful workflow guidance without memorizing skill
names or adding one large instruction pack to every coding session.

Each workflow has its own `SKILL.md`. Clear requests continue automatically. When a
request could mean materially different work, the user sees two or three plain-language
outcomes instead of an internal list of skill names.

![Automatic workflow: describe a task normally, let the adaptive router select and combine focused skills, and receive an evidence-backed result.](docs/assets/skills-workflow.svg)

*Workflow illustration, not an application screenshot. The skills guide the agent inside your existing development project.*

[Get started](#quick-start) · [Automatic routing](#how-automatic-routing-works) · [Try a task](#try-a-task) · [All workflows](#skills) · [Development](#development) · [License](LICENSE) · [Credits](docs/SOURCES.md)

## Quick start

1. Clone this repository or download its source ZIP.
2. Copy the skill folders you want from `.agents/skills/` into the same location in your project. Copy the whole folder, including `references/` and `agents/` when present.
3. Merge [AGENTS.snippet.md](AGENTS.snippet.md) into your project's existing `AGENTS.md`. If the project has none, create it from the snippet.
4. Open Codex in your project and describe the task normally:

```text
The checkout page becomes blank after a browser refresh. Reproduce the problem,
fix its cause, and verify the original flow.
```

The router should announce a short workflow such as **Browser Diagnostics →
Systematic Debugging → Verification**, then continue. If “improve the checkout page”
could mean a bug fix, a visual change, or a redesign, it should recommend a
plain-language outcome and let the user choose.

The discovery path in the target project must be `.agents/skills/<skill-name>/SKILL.md`. Do not copy this repository as an extra nested folder and expect its skills to apply to the parent project. Codex detects skill changes; restart it if the new skills do not appear. See the [official local-skills documentation](https://learn.chatgpt.com/docs/build-skills).

On macOS, press Command-Shift-period to show the hidden `.agents` folder. Merge existing directories carefully. Same-name skills from different locations do not merge; keep one active copy.

## How automatic routing works

The router uses the request, repository instructions, and skill descriptions. It does
not use a fixed keyword list and it does not treat choosing a workflow as permission
for broader work.

```mermaid
flowchart TD
    A[Describe the task normally] --> B[Adaptive workflow reads intent and boundaries]
    B --> C{How clear is the outcome?}
    C -->|Clear| D[Announce the smallest skill chain and continue]
    C -->|Several different outcomes| E[Recommend 2 or 3 outcome-based choices]
    C -->|Missing information blocks progress| F[Ask one concise question]
    E -->|User chooses| B
    F -->|User clarifies| B
    D --> G[Read only the selected skill instructions]
    G --> H[Work within the requested scope]
    H --> I[Report evidence, checks, and gaps]
```

High-confidence routing does not create an extra approval ritual. Diagnosis, review,
and planning requests keep their requested scope: “diagnose only” produces findings,
not an unauthorized fix. The router normally selects one primary skill and no more
than two supporting skills.

## Try a task

Open a scenario below, replace the bracketed input, and paste the prompt into Codex from your project. These are illustrative walkthroughs, not recorded executions or guaranteed results.

<details>
<summary><strong>Fix a failing test</strong> — reproduce → explain → change → verify</summary>

```text
[Failing scenario] now fails with this output: [relevant output].
Reproduce it, find the cause, make the smallest appropriate fix, and check the
original case before handing it back.
```

Look for a reproduction when the environment permits, a cause tied to the affected code, a focused fix and a check of the original case. If a dependency is unavailable, the agent should say which check it could not run.

</details>

<details>
<summary><strong>Understand an unfamiliar app</strong> — input → processing → storage → response</summary>

```text
Trace [endpoint or UI action] through validation, transformations, storage, and the
response. Show a diagram and link the explanation to the relevant source. Do not
edit code.
```

Look for a source-backed flow with unknowns labeled. Static inspection explains the implementation; it should not be presented as a captured runtime trace.

</details>

<details>
<summary><strong>Shape a feature before building it</strong> — inspect → decide → define acceptance</summary>

```text
Plan [feature]. Inspect the current flow, ask only questions that would change the
design, and produce observable acceptance criteria. Planning only.
```

Look for the decisions that affect scope and a small set of testable outcomes. When you are ready to implement, ask for the chosen change explicitly.

</details>

For more prompts, including review, browser diagnosis and resumable work, see [Try the skills in Codex](docs/TRY-IT.md).

## Skills

| Skill | Use it for | What you get |
| --- | --- | --- |
| [adaptive-workflow](.agents/skills/adaptive-workflow/SKILL.md) | Natural-language routing and multi-skill composition | Automatic continuation or a small outcome-based choice |
| [lean-senior-engineering](.agents/skills/lean-senior-engineering/SKILL.md) | Implementation, refactoring, review, audit, technical debt | Small complete changes, focused checks, prioritized findings |
| [systematic-debugging](.agents/skills/systematic-debugging/SKILL.md) | Bugs, failing tests, build failures | Reproduction, supported cause, focused fix when requested |
| [verification-before-completion](.agents/skills/verification-before-completion/SKILL.md) | Implementation handoff, verification requests | Actual check results and clearly stated gaps |
| [feature-discovery](.agents/skills/feature-discovery/SKILL.md) | Ambiguous features, consequential design choices | Decisions and observable acceptance criteria |
| [research-plan-implement](.agents/skills/research-plan-implement/SKILL.md) | Changes across modules or sessions | Code-backed research, execution plan, resumable handoff |
| [architecture-map](.agents/skills/architecture-map/SKILL.md) | Architecture, data processing, change impact | Diagrams connected to real source evidence |
| [release-readiness](.agents/skills/release-readiness/SKILL.md) | Pre-release assessment | Scoped readiness decision, blockers, rollout considerations |
| [browser-diagnostics](.agents/skills/browser-diagnostics/SKILL.md) | UI, console, network, browser performance | Reproduction evidence and an explanation of the failing path |

Start with a representative task in ordinary language. The router and concise skill
descriptions let Codex select matching workflows automatically. See [natural-language
examples and expected behaviour](docs/TRY-IT.md).

## Design

- Reuse the repository's patterns and dependencies before introducing new ones.
- Route by user outcome and consequence, not a hard-coded keyword count.
- Continue automatically for a clear task; offer choices only when outcomes differ.
- Complete the requested behaviour, including affected callers and meaningful checks.
- Diagnose from evidence and report the scope of verification.
- Keep reviews and diagnosis separate from implementation when the user requests findings only.
- Keep detailed references out of the initial skill context until needed.

The pack contains workflow instructions and optional UI metadata. It does not install hooks, a browser, an MCP server, or an application test framework. Browser diagnostics requires available browser tooling or an existing browser-test setup. Architecture diagrams use available rendering tools and disclose when rendering was not verified.

These workflows are independently maintained files informed by the projects credited in [Sources](docs/SOURCES.md). This is an independent project, with no affiliation with OpenAI or the credited upstream projects. It does not reproduce their full plugins, dashboards, or benchmark results.

## Repository layout

```text
.agents/skills/       Adaptive router, workflow skills, references, and UI metadata
.github/             CI, issue forms, and pull-request template
docs/                Trial prompts, sources, publishing, validation
scripts/             Structure validator and release archive builder
tests/               Validation, routing-policy, and packaging tests
AGENTS.md            Guidance for maintaining this repository
AGENTS.snippet.md    Guidance to merge into a consuming project
```

Copy the skills and snippet into your application. Keep this repository's maintenance `AGENTS.md`, CI, and tooling in the skills repository.

## Development

Using the skills requires no Python packages. Maintaining this repository requires Python 3.9+ and the development dependency below:

```sh
python3 -m venv .venv
# macOS/Linux:
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/validate_skills.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/build_release.py
```

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`.

The validator checks metadata, directory/name agreement, natural default prompts,
optional invocation policy, portable references, and local links. Routing tests check
the installed names, chain-size rule, interaction modes, consuming-project policy,
and a natural-language prompt corpus. Structural checks do not prove that every model
will make the same routing decision; representative model trials are recorded in
[validation scope](docs/VALIDATION.md). CI runs the same validation and tests on pushes
and pull requests.

The archive builder writes a versioned source ZIP and SHA-256 checksum to `dist/`, using an explicit list of distributable paths. It excludes local Git history, virtual environments, working artifacts, and operating-system files.

## Status and contributing

Initial version: **0.1.0**. Read [validation scope](docs/VALIDATION.md), [change history](CHANGELOG.md), and the [contribution guide](CONTRIBUTING.md). Behaviour varies with the model, application, and available tools; report a reproducible example when a workflow misbehaves.

To publish your own copy, follow [Publishing to GitHub](docs/PUBLISHING.md). For vulnerabilities or unintended sensitive-data exposure, see [Security](SECURITY.md).

## License

[MIT](LICENSE), copyright 2026 Raditte Anggoro and contributors. Read the
[project notice](NOTICE.md), [third-party notices](THIRD_PARTY_NOTICES.md), and
[inspiration/source record](docs/SOURCES.md). Credits acknowledge ideas and capability
comparisons; they do not claim affiliation or import upstream code into this project.
