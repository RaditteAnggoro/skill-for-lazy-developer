# Claude Code lifecycle adapter

This adapter uses Claude Code's user-level `settings.json` hook schema for the same
Engram memory runtime as Codex. It is the final host increment in Phase 3.

## Hooks

- `SessionStart`: recalls a bounded Engram context before the first prompt.
- `UserPromptSubmit`: handles explicit remember, show, project opt-out, and
  confirmation-gated forget controls.
- `Stop`: writes a bounded handoff from `last_assistant_message`; it is verified only
  with linked transcript evidence.

The runtime is shared with the Codex adapter and is fail-open.

## Setup

Prerequisites:

- Claude Code with hooks support;
- Engram installed or an absolute binary path;
- Python 3.9+;
- an Engram project in the repository (`.engram/config.json`):

```sh
engram init <project-name>
```

Install:

```sh
python scripts/install_claude_adapter.py check --claude-home "$HOME/.claude"
python scripts/install_claude_adapter.py install \
  --claude-home "$HOME/.claude" \
  --engram-bin "$(command -v engram)"
```

This writes:

- `~/.claude/settings.json` (merged with existing settings and hooks);
- `~/.claude/companion-memory/memory_runtime.py`;
- `~/.claude/companion-memory/config.json`.

Existing settings are backed up. The installer does not edit project settings; it
uses the user scope so it works across projects. Review the added commands before
enabling them; Claude Code runs command hooks from user settings.

Verify:

```sh
python scripts/install_claude_adapter.py check \
  --claude-home "$HOME/.claude" \
  --project /path/to/repository
```

## Controls

```text
Remember this: billing uses PostgreSQL.
Show what you remember.
Do not remember this project.
Forget the billing decision.
```

`Forget` requires a second confirmation before deletion.

## Uninstall and rollback

```sh
python scripts/install_claude_adapter.py uninstall --claude-home "$HOME/.claude"
python scripts/install_claude_adapter.py rollback \
  --claude-home "$HOME/.claude" --backup <backup-directory>
```

Uninstall removes only this adapter's handlers and private runtime/config files.

## Verification status

The hook configuration and shared runtime are unit-tested with real Claude hook JSON
shapes. **No Claude Code binary or authenticated session is available on this machine**,
so live model delivery is explicitly unverified. Details are in
[`docs/CLAUDE_ADAPTER_EVIDENCE.md`](../../docs/CLAUDE_ADAPTER_EVIDENCE.md).
