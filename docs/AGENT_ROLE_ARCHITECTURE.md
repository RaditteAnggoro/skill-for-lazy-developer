# Agent role architecture

## Separation

- **Intent** is owned by `adaptive-workflow`.
- **Method** is owned by the existing 17 skills.
- **Tool capability** is selected by `tool-selection.md`.
- **Role** is a provider-neutral advisory contract for bounded independent evidence.
- **Evidence** is verified by existing verification and test infrastructure.
- **Learning** is a proposal, never an automatic active-skill edit.

Roles are not skills and do not consume the per-phase skill quota. They are not a second
router. The parent agent remains the system of record.

## Four initial roles

| Role | Bounded purpose | Mandatory boundary |
| --- | --- | --- |
| `ld-codebase-explorer` | Read-heavy impact/caller mapping | Read-only; source anchors and unknowns |
| `ld-independent-test-reviewer` | Independent test/evidence review | Read-only; PASS/FAIL/BLOCKED/NOT_TESTED |
| `ld-financial-integrity-reviewer` | Idempotency, retry, ledger, reconciliation review | Read-only; no production DB or writes |
| `ld-workflow-tool-evaluator` | Compare routing/tool quality and overhead | Offline/local evidence; no config mutation |

The contracts live in [`.agents/roles/`](../.agents/roles/). Validate with
`python scripts/validate_roles.py`. Render host wrappers with
`python scripts/render_agent_adapters.py --host codex --check` and
`--host claude --check`.

## Critical security boundary

`write_permission: false` and `denied_capabilities` are **policy metadata, not a
sandbox**. A host may still expose write-capable tools. If read-only behavior cannot be
enforced by the host, do not dispatch the role; use the main-agent read-only fallback or
return `BLOCKED` / `permission_restricted`.

## Host support

- **Codex** (verified locally `0.167.0`): project TOML wrappers are generated under
  `.codex/agents/`; the host must be restarted/loaded according to its supported
  discovery behavior. No user-home installation.
- **Claude Code** (verified locally `2.1.322`): project Markdown wrappers under
  `.claude/agents/` use `Read, Grep, Glob` only. Discovery depends on the installed
  host; restart/trust review may be required.
- **DeepSeek Harness**: no verified subagent API in the implemented adapter. Use the
  role as a sequential rubric, label the trace
  `execution_mode=single-agent-role-guided`, and preserve memory hooks.
- **Hermes**: not a runtime dependency.

## Resource and delegation policy

Default zero specialists for simple tasks, one when clearly useful, and at most two
concurrent independent specialists. No recursive fan-out. No parallel writes to shared
files. Freeze contracts before parallel read-only review. Treat every specialist result
as untrusted evidence and reconcile it with source/tests.

Generated wrapper inventory: [.claude/agents/README.md](../.claude/agents/README.md).
