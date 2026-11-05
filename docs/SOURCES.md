# Sources and capability boundaries

These independently maintained workflows were first assembled on 2026-10-28. The projects below inform the selected practices and are credited for comparison. Their original plugins, hooks, services, and renderers are not bundled here.

| Reference | Practices reflected here | Upstream capabilities not bundled |
| --- | --- | --- |
| [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | Minimal complete changes, reuse preference, implementation levels, focused checks, reviews and shortcut/debt awareness | Original prompt, slash-command adapters, hooks, dashboard, measurements, plugin state |
| [obra/superpowers](https://github.com/obra/superpowers) | Root-cause investigation, regression checks, verification evidence, incremental testing | Full mandatory methodology, original skill collection, hooks and agent orchestration |
| [mattpocock/skills](https://github.com/mattpocock/skills) | Consequential feature questions, observable acceptance criteria, shared terminology, short test feedback cycles | Full engineering collection, setup command, tracker actions and orchestration |
| [humanlayer/skills](https://github.com/humanlayer/skills) | Research, planning, implementation, and resumable local records | Original RPI implementation, automatic fresh-session execution and upstream integrations |
| [tt-a1i/archify](https://github.com/tt-a1i/archify) | Diagrams that help explain code and data paths | Archify renderer, interactive viewer, validation utilities and export pipeline |
| [ChromeDevTools/chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) | Browser console/network evidence, interaction reproduction, measured performance | MCP server, Chrome, tooling installation and configuration |

`lean-senior-engineering` combines a short entrypoint with optional references for test design, reviews, audits, and debt. Repository copies are independent of any same-name personal skill.

## OpenAI documentation used for packaging

- [Build skills](https://learn.chatgpt.com/docs/build-skills): local `.agents/skills`
  discovery, required metadata, progressive disclosure, implicit invocation,
  optional UI policy, and duplicate-name behaviour.
- [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md): repository instructions and scope.
- [Build focused skills](https://developers.openai.com/plugins/build/skills): concise entrypoints, supporting references, workflow boundaries, representative testing.
- [Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills): positive, contextual, and negative prompt cases plus trace-based evaluation guidance.

The adaptive router and routing policy are original implementation choices in this
repository, informed by the documented implicit-invocation model. Skill availability
and actual tool access are separate: instructions cannot provide an absent browser,
network access, a database connection, or a running application.

The sources evolve. For full upstream behaviour, install and review the relevant upstream project separately and follow its current license and setup instructions. This pack makes no claim to reproduce upstream benchmarks or every plugin feature.

## Version 2 research references

The research table records capability comparisons only; it does not bundle, install,
or copy implementation from these projects.

| Reference | Evaluated idea | Current decision |
| --- | --- | --- |
| [akitaonrails/ai-memory](https://github.com/akitaonrails/ai-memory) | Lifecycle capture, MCP memory, session handoff | Phase 2 alternate; 3.4.0 measured, not bundled |
| [Gentleman-Programming/engram](https://github.com/Gentleman-Programming/engram) | Curated local memory, SQLite/FTS, MCP | Selected for the first Phase 3 adapter; 3.6.2 measured, not bundled |
| [rtk-ai/rtk](https://github.com/rtk-ai/rtk) | Development-command output filtering | Phase 4 research candidate; upstream savings are not project results |
| [mksglu/context-mode](https://github.com/mksglu/context-mode) | Keeping large tool output outside active context | Phase 4 research candidate; compatibility and privacy review required |
| [oraios/serena](https://github.com/oraios/serena) | Symbol-level source retrieval | Phase 4 integration candidate; not a replacement for focused file reads |
| [yamadashy/repomix](https://github.com/yamadashy/repomix) | Scoped repository snapshots and token counts | Evaluation utility candidate, not an always-loaded context source |
| [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | Searchable UI design guidance | Phase 5 design research; no content imported |
| [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | React implementation, performance, web design review | Phase 5 implementation research; no content imported |
| [trailofbits/skills](https://github.com/trailofbits/skills) | Specification compliance and property-based testing | Phase 6 workflow research; no content imported |
| [getsentry/skills](https://github.com/getsentry/skills) | Skill security scanning | Phase 6 security research; no scanner bundled |
| [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) | Agent evaluation and token reporting | Later evaluation candidate; Phase 0 keeps the existing lightweight harness |

The Phase 2 bake-off used official release binaries for ai-memory 3.4.0 (MIT) and
Engram 3.6.2 (MIT). Their published SHA-256 checksums were verified before execution.
The binaries and provider data were kept in ignored local artifacts and are not part
of this repository's source archive. The adapter, schema, and benchmark are original
to this project; the providers' code and documentation were not copied. The recorded
comparison and its limits are in [`V2_PHASE2_EVIDENCE.md`](V2_PHASE2_EVIDENCE.md).

The Claude adapter uses the documented Claude Code hook contract at
[`code.claude.com/docs/en/hooks`](https://code.claude.com/docs/en/hooks); it does not
copy Claude Code source. The DSH adapter targets DeepSeek Harness's native skill filesystem, instruction,
MCP client, and profile bundle surfaces. It was verified against DSH
`0.2.1-rc.5` and Engram 3.6.2; no DSH source is copied or redistributed here.

Every later phase must re-check current upstream behaviour, license, privacy,
permissions, and supply-chain risk before adopting a dependency or transforming
source material.

## Test tooling

UI fixture checks use Playwright Core, pngjs, and pixelmatch as development-only
dependencies. They are not vendored into the distributed skill instructions.
