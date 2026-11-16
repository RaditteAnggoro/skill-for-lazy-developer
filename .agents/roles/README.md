# Provider-neutral role contracts

Roles answer **who may inspect or independently review**. Skills answer **how to do the
work**. A role is not a new skill, router, or permission grant.

These four contracts are advisory, read-only specialist roles. The parent agent keeps
implementation ownership and final synthesis. Host wrappers in `.codex/agents/` and
`.claude/agents/` are generated from these YAML files; they do not install into user
home or alter global settings.

```sh
python scripts/validate_roles.py
python scripts/render_agent_adapters.py --host codex --check
python scripts/render_agent_adapters.py --host claude --check
```

`write_permission: false` and `denied_capabilities` are policy metadata. They are not a
sandbox. Check the host's actual permissions; if a role cannot be restricted, use the
single-agent read-only fallback instead of dispatching it.

| Role | Use when | Default |
| --- | --- | --- |
| `ld-codebase-explorer` | A large, bounded exploration would pollute the parent context | Read-only impact map |
| `ld-independent-test-reviewer` | A meaningful change needs independent evidence review | PASS/FAIL/BLOCKED/NOT_TESTED |
| `ld-financial-integrity-reviewer` | Money, ledger, retry, batch, or reconciliation risk | Read-only invariants and failure modes |
| `ld-workflow-tool-evaluator` | Repeated routing/tool inefficiency or a measured comparison | Comparative findings and metrics |

Single-agent fallback is required on hosts without supported delegation. DSH may use the
role as a sequential review rubric and must label it `execution_mode=single-agent-role-guided`.
