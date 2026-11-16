# Phase 2–3 evidence — roles, wrappers, and selective delegation

## Phase 2: role contracts and adapters

- Four provider-neutral contracts validate with `python scripts/validate_roles.py`.
- All initial roles are read-only by policy: `write_permission: false`,
  `external_side_effects: false`, and `filesystem-write`/`remote-push` denied.
- Unknown fields, write-enabled roles, empty triggers, bad scopes, invalid statuses, and
  missing source-citation requirements are rejected.
- Codex TOML and Claude Markdown wrappers parse and are byte-for-byte deterministic.
- Claude wrappers use only `Read, Grep, Glob`; wrappers contain no model selection,
  sandbox-mode declaration, user-home path, or credential.
- Role contracts are opt-in in the portable pack (`--with-roles`). The default pack
  remains unchanged. Existing role files are backed up on collision and restored by
  rollback.
- Policy is not a sandbox. Host permissions must be checked before dispatch.

## Phase 3: selective delegation

The eight-case decision table passes:

| Case | Decision |
| --- | --- |
| One-line edit | single |
| Simple explanation | single |
| Financial restart | delegate to financial integrity reviewer |
| Large impact map | delegate to codebase explorer |
| Independent review | delegate to test reviewer |
| Unsupported host | single-agent role-guided fallback |
| Unreadable permissions | fallback with `permission_restricted` |
| Low-value parallel | single |

Traces are explicitly `evidence_level: SIMULATED` and `live_dispatch: false`. A delegated
trace says `execution_mode=simulated-delegation`; a fallback says
`execution_mode=single-agent-role-guided`. No live host dispatch is claimed.

## Host status

- Codex 0.167.0: wrapper parse only; custom role dispatch **NOT_RUN**.
- Claude 2.1.322: wrapper parse; `loggedIn: false`; live dispatch **AUTH_REQUIRED**.
- DSH: no verified subagent API; **UNSUPPORTED**, single-agent rubric.
- Hermes: not required.

## Limits

- No live role dispatch, no live Claude session, and no host permission experiment.
- No production DB, browser payment, or external side effect was exercised.
- The decision table is a policy simulation, not evidence of model compliance.
