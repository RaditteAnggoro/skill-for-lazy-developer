# Codex lifecycle adapter

This adapter connects Codex's stable lifecycle hooks to Engram project memory. It is
the shared Phase 3 vertical slice; DSH and Claude adapters are separate host increments.

## What it does

- `SessionStart`: recalls a bounded Engram context and injects it as additional
  developer context. No memory command is needed.
- `UserPromptSubmit`: handles ordinary-language controls:
  - `Remember this: ...` saves an explicit user decision.
  - `Show what you remember` / `Apa yang kamu ingat` recalls context.
  - `Do not remember this project` / `Jangan ingat proyek ini` disables memory for
    that project.
  - `Forget ...` shows candidates; a second `forget confirm <id>` deletes after explicit
    confirmation.
- `Stop`: saves a bounded handoff. It is promoted to `verified` only when a
  verification command and success marker are linked to the session transcript;
  otherwise it remains `unverified`.

All hooks are fail-open: a missing Engram, malformed input, timeout, or runtime error
does not block ordinary Codex work.

## One-time setup

Requirements:

- Codex with lifecycle hooks enabled;
- Engram installed or an absolute Engram binary path;
- Python 3.9+;
- an Engram project initialized in the repository:

```sh
engram init <project-name>
```

Install the user-level adapter:

```sh
python scripts/install_codex_adapter.py check --codex-home "$HOME/.codex"
python scripts/install_codex_adapter.py install \
  --codex-home "$HOME/.codex" \
  --engram-bin "$(command -v engram)"
```

The installer writes:

- `~/.codex/hooks.json` (merged with existing hooks);
- `~/.codex/codex-memory/memory_runtime.py`;
- `~/.codex/codex-memory/config.json`.

It backs up existing files and does **not** mark the hooks trusted. In Codex, run
`/hooks` once, review the three definitions, and trust them. Project `.codex` hooks are
not used, so this adapter works from any trusted project with an Engram config.

Verify:

```sh
python scripts/install_codex_adapter.py check \
  --codex-home "$HOME/.codex" \
  --project /path/to/repository
```

## Controls

```text
Remember this: billing uses PostgreSQL, not MySQL.
Show what you remember.
Do not remember this project.
Forget the billing database decision.
```

`Forget` is a two-step control; deletion happens only after `forget confirm <id>`.

## Fail-open and recovery

If Engram is missing, the hooks return no context and exit successfully. Codex keeps
working. The runtime never prints a traceback to stdout.

```sh
python scripts/install_codex_adapter.py uninstall --codex-home "$HOME/.codex"
python scripts/install_codex_adapter.py rollback \
  --codex-home "$HOME/.codex" --backup <backup-directory>
```

`uninstall` removes only this adapter's hook handlers and runtime/config files. It
preserves unrelated hooks.

## Verification

The standard end-to-end check uses a disposable `CODEX_HOME`, a real Engram store,
and the Codex CLI:

```sh
python scripts/verify_codex_adapter.py \
  --engram-bin /path/to/engram \
  --artifacts .agents/artifacts/codex-verification
```

For automation it passes `--dangerously-bypass-hook-trust`; that flag is **not** part
of normal installation. Real users must review hooks with `/hooks`.

Results and limits are in
[`docs/CODEX_ADAPTER_EVIDENCE.md`](../../docs/CODEX_ADAPTER_EVIDENCE.md).
