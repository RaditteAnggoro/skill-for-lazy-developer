# Claude Code adapter evidence

Date: **2026-11-05** (Asia/Jakarta)

Status: **Claude adapter implemented and hook-contract tested; live Claude model
delivery is deferred.** Phase 3 is complete with `verified-with-deferred-claude`.

## Environment

- macOS 27.2 on arm64.
- Python `3.9.6`.
- Engram `3.6.2` (shared store implementation).
- No `claude` binary and no `~/.claude` authenticated profile were available.

The test therefore exercises the **Claude hook JSON contract** and the shared
runtime directly. It does not claim an end-to-end Claude model run.

## Verified adapter behavior

| Check | Result |
| --- | --- |
| `settings.json` hook merge | Pass |
| Existing hooks/settings preserved | Pass |
| Installer idempotent | Pass |
| Uninstall removes only adapter handlers | Pass |
| Rollback restores edited settings | Pass |
| `SessionStart` recall output | Pass |
| `UserPromptSubmit` remember/opt-out | Pass |
| `Stop` bounded handoff | Pass |
| Missing Engram fail-open | Pass |
| Sensitive write skipped | Pass |

The runtime writes the same JSON shapes Claude documents:

- `SessionStart` → `hookSpecificOutput.additionalContext`;
- `UserPromptSubmit` → `hookSpecificOutput.additionalContext`;
- `Stop` → `{}` after saving a conditional handoff; without linked evidence it remains
  `unverified`.

## Limits

- **No live Claude Code binary or authenticated model run.** The hook contract is
  verified, not model delivery.
- The handoff is conditional on verification evidence; live Claude delivery was not
  observed.
- `forget` is a two-step, confirmation-gated deletion in the shared runtime.
- The adapter relies on a project `.engram/config.json`; projects without it are
  skipped.
- User-level settings are machine-local; they are not a team-shared configuration.
- One test run, one Python/Engram version.

## Reproduction

```sh
python scripts/install_claude_adapter.py check --claude-home "$HOME/.claude"
python -m unittest tests.test_claude_adapter tests.test_claude_evidence -v
```

The installer is in `scripts/install_claude_adapter.py`; the shared runtime is
`integrations/codex/memory_runtime.py`.
