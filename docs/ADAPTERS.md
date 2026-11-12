# Host adapters

The workflow files are host-neutral Markdown, but discovery, instructions, UI
metadata, memory, and lifecycle hooks are host-specific. This page records what works
without an adapter and what each host needs.

## Compatibility matrix

| Capability | Codex / OpenAI | Claude Code | DeepSeek Harness (DSH) |
| --- | --- | --- | --- |
| Workflow content (`SKILL.md`) | Yes | Yes, when loaded | Yes |
| Project instructions | `AGENTS.md` | `CLAUDE.md` and host configuration | `AGENTS.md` or `CLAUDE.md` |
| Project skill discovery | `.agents/skills` | Requires a Claude skill/plugin path | `.agents/skills` is a default root |
| UI metadata | `agents/openai.yaml` | Not used | Ignored |
| Adaptive routing corpus | Shared | Shared, but re-evaluate | Shared plus DSH overlay |
| Persistent memory | Phase 3 Codex adapter | Phase 3 Claude adapter | Engram MCP + DSH lifecycle plugin |
| Lifecycle hooks | Codex hooks implemented | Claude hooks implemented | DSH agent lifecycle implemented |
| Automatic recall | Codex `SessionStart` | Claude `SessionStart` | DSH pre-step with prompt |
| Handoff | Codex `Stop` conditional | Claude `Stop` conditional | DSH `agent/turn-stopping` conditional |

A check mark for "workflow content" means the instructions are portable. It does not
mean a host automatically discovers every file or provides the same tools.

The shared [tool-selection policy](../.agents/skills/adaptive-workflow/references/tool-selection.md)
uses capabilities rather than host-specific MCP names. Each host must expose and
authenticate its own tools; the portable pack neither installs nor configures them.
Fallback and security instructions are portable guidance, not a runtime guarantee.
Live MCP invocation and cross-host model adherence require separate verification.

## Portable skill layer

The host-neutral layer can be exported and imported without copying hooks or memory:

```sh
python scripts/package_skill_pack.py export --output dist/skill-pack.zip
python scripts/package_skill_pack.py import dist/skill-pack.zip --target /path/to/project
```

The pack contains skills, UI metadata, the consuming snippet, adapter docs, and license
notices. It verifies file hashes, rejects traversal/duplicate paths, backs up replaced
files, and supports rollback. See [PORTABLE_PACK.md](PORTABLE_PACK.md). The portable layer
does not install hooks, trust hooks, or copy credentials.

## Codex / OpenAI

Use the existing repository layout:

- merge [AGENTS.snippet.md](../AGENTS.snippet.md) into the project's `AGENTS.md`;
- copy workflow directories under `.agents/skills/`;
- keep `agents/openai.yaml` only for OpenAI UI metadata;
- use the Codex routing runner in Phase 1 for model trials.

Phase 3 adds the Codex lifecycle adapter:

- [adapters/codex/README.md](../adapters/codex/README.md);
- [integrations/codex/memory_runtime.py](../integrations/codex/memory_runtime.py);
- [scripts/install_codex_adapter.py](../scripts/install_codex_adapter.py);
- [scripts/verify_codex_adapter.py](../scripts/verify_codex_adapter.py).

The installer merges `SessionStart`, `UserPromptSubmit`, and `Stop` into the
user-level Codex hooks file. It does not trust them: the user must review `/hooks`
once. The adapter is fail-open and only operates in a project with an Engram
`.engram/config.json`.

## Claude Code

Claude Code reads its own instruction and plugin conventions; it does not share all of
Codex's layout. The hook contract is documented at
[code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks). Keep the Markdown workflows as the portable core, then add a Claude
adapter that:

- imports the shared instructions into `CLAUDE.md` or the host's supported import
  mechanism;
- exposes the same skill names through the Claude skill/plugin surface;
- keeps hooks, slash commands, and MCP configuration Claude-specific;
- runs the same routing corpus against the selected Claude model.

Phase 3 adds a Claude Code adapter:

- [adapters/claude/README.md](../adapters/claude/README.md);
- [scripts/install_claude_adapter.py](../scripts/install_claude_adapter.py);
- the shared runtime at
  [integrations/codex/memory_runtime.py](../integrations/codex/memory_runtime.py).

It merges `SessionStart`, `UserPromptSubmit`, and `Stop` into the user-level
`~/.claude/settings.json`. No Claude Code binary or authenticated session was
available for a live model run; the hook contract and installer are tested directly.

## DeepSeek Harness (DSH)

DSH has two separate integration layers. They should not be conflated.

### 1. Skill and instruction adapter

A DSH profile that mounts `@deepseek-ai/dsh-skill-filesystem`,
`@deepseek-ai/dsh-tool-skill`, and `@deepseek-ai/dsh-agent-instructions` automatically
discovers:

- `<project>/.agents/skills/*/SKILL.md`;
- `<project>/.dsh/skills/*/SKILL.md` (higher priority);
- `AGENTS.md` and `CLAUDE.md`.

The repository adapter makes this explicit and reproducible:

```sh
python scripts/dsh_adapter.py check --root .
python scripts/dsh_adapter.py install --root . --dry-run
python scripts/dsh_adapter.py install --root .
python scripts/dsh_adapter.py uninstall --root .
python scripts/dsh_adapter.py rollback --root . --backup <backup-file>
```

`install` merges [AGENTS.snippet.md](../AGENTS.snippet.md) plus
[adapters/dsh/AGENTS.dsh.md](../adapters/dsh/AGENTS.dsh.md) into one marked block. The
block is idempotent, backed up before modification, and removable without touching the
rest of `AGENTS.md`.

`agents/openai.yaml` is ignored by DSH. The shared `SKILL.md` frontmatter is what DSH
uses.

### 2. Memory runtime adapter

The DSH memory bundle lives at
[`integrations/dsh/companion-memory`](../integrations/dsh/companion-memory):

- connects Engram through `@deepseek-ai/dsh-mcp-client`;
- exposes Engram's `mcp__engram__*` tools;
- adds a Host guard that rejects obvious secrets, customer email addresses, private
  keys, oversized content, and raw prompt capture before `mem_save`/`mem_update`/
  session summaries reach the provider;
- sets `failOnStartupError: false` so missing Engram does not block ordinary work;
- adds a short memory policy to the system prompt;
- prepares recall on `agent/created`, injects it with the actual prompt on
  `agent/pre-step`, and writes a conditional handoff on `agent/turn-stopping`.

Install it in a DSH profile:

```sh
dsh plugin --profile <profile> add /absolute/path/to/integrations/dsh/companion-memory
dsh --profile <profile> --dump-config | grep -E 'engram-(mcp|guard)'
```

Uninstall it:

```sh
dsh plugin --profile <profile> remove @local/dsh-companion-memory
```

Installing a bundle executes Host code and requires the host's normal approval or Full
access. Review the code first. The bundle is local-only and does not download, install,
or configure Engram itself.

## Verification standard

The DSH adapter is verified against the standard below, not a three-prompt smoke test.
The recorded evidence is in [DSH adapter evidence](DSH_ADAPTER_EVIDENCE.md).

| Area | Standard |
| --- | --- |
| Skill discovery | All sixteen workflows appear with valid frontmatter |
| Instruction merge | Idempotent install, check, uninstall, rollback, user content preserved |
| Routing | Entire 24-case corpus, not a three-case sample |
| Read-only boundaries | Diagnosis and architecture prompts do not authorize edits |
| Interaction | Ambiguous requests remain interactive; clear planning stays automatic |
| Memory | Codex recall, explicit remember, bounded handoff, restart, delete, and isolation |
| Privacy | Guard rejects a synthetic canary in unit/bundle checks; direct provider and live DSH behavior are reported separately |
| Failure | Missing provider leaves ordinary DSH work usable |
| Packaging | Bundle installs into a disposable profile, rows appear, remove leaves no rows, and DSH still works |
| Claude hooks | Settings merge, controls, recall/handoff shapes, fail-open, and uninstall tested; live Claude deferred |

## Known limits

- DSH must mount its skill/instruction plugins; a stripped profile may not discover
  project skills.
- The Host guard is pattern-based. It is a safety boundary, not a complete DLP system.
- Engram itself accepted the synthetic canary in the direct MCP test. The guard is
  therefore mandatory, not optional.
- The bundle implements automatic recall and a bounded handoff. Live delivery is
  verified; handoff verification is conditional on transcript evidence.
- The DSH routing trial uses one profile and one repetition. Re-run it after changing
  the model, profile, instructions, or skill descriptions.
- The adapter does not make Claude Code or Codex configurations interchangeable.
