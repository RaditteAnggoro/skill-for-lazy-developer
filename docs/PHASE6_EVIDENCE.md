# Phase 6 evidence — cross-host validation and documentation

## Static host validation

| Check | Result |
| --- | --- |
| Codex TOML role wrappers parse with `tomli` | 4/4 |
| Claude Markdown frontmatter parse with PyYAML | 4/4 |
| Claude tools restricted to `Read, Grep, Glob` | 4/4 |
| No model/sandbox-mode/user-home/credential fields in wrappers | pass |
| Role validator rejects unsafe contracts | pass |
| Portable pack default remains valid | pass |
| Optional roles are opt-in and collision-safe | pass |

## Host integration status

| Host | Local observation | Status |
| --- | --- | --- |
| Codex CLI 0.167.0 | logged in; no supported non-interactive custom-role dispatch exercised | `NOT_RUN` |
| Claude Code 2.1.322 | installed; `loggedIn: false` | `AUTH_REQUIRED` |
| DSH | adapter target; no verified subagent API | `UNSUPPORTED` |
| Hermes | not required | not a dependency |

`tests/host_integration_status.yaml` is the machine-readable status. No host role was
installed into user home or global settings.

## Documentation

- [role architecture](AGENT_ROLE_ARCHITECTURE.md)
- [Hermes enhancement mapping](HERMES_INSPIRED_ENHANCEMENTS.md)
- [learning/evaluation](LEARNING_AND_EVALUATION.md)
- [adapter guide](ADAPTERS.md)
- [implementation report](HERMES_IMPLEMENTATION_REPORT.md)

## Limits

Host dispatch and live role behavior remain unverified. The wrappers are not credited as
runtime-enforced read-only sandboxes. No real browser/DB/payment task was run.
