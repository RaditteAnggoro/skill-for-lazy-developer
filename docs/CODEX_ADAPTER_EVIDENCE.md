# Codex adapter evidence

Date: **2026-11-05** (Asia/Jakarta)

Status: **Phase 3 Codex vertical slice standard-verified; Phase 3 remains
`in-progress`.** DSH lifecycle hooks are unit-tested and Claude hooks are
configuration-tested; live DSH/Claude model delivery was not observed.

## Environment

- Codex CLI `0.166.0-alpha.6`.
- Model `gpt-6.1-sol`.
- Engram `3.6.2` official release.
- macOS 27.2 on arm64.
- Python `3.9.6`.
- Disposable `CODEX_HOME`, project, Engram data, and session.

The end-to-end check uses a real model call. The user's `~/.codex/auth.json` is
symlinked into the disposable home, not copied into the repository.

## Verified lifecycle

| Check | Result |
| --- | --- |
| `SessionStart` recall | Pass |
| `UserPromptSubmit` explicit remember | Pass |
| `Stop` bounded handoff | Pass |
| Missing Engram fail-open | Pass |
| Project opt-out control | Pass |
| Uninstall removes hooks/runtime | Pass |
| Sensitive write skipped | Pass |
| Installer idempotent | Pass |
| Installer rollback | Pass |
| Existing unrelated hooks preserved | Pass |

The actual end-to-end run returned `RECALL-TOKEN-7319` from the injected
`SessionStart` context, stored the explicit `Phase 3 uses a bounded handoff` note,
stored a `Session handoff: demo` record on `Stop`, answered `OK` with Engram missing,
recorded the project opt-out, and left no adapter hooks after uninstall.

## Hook trust

The installer merges `SessionStart`, `UserPromptSubmit`, and `Stop` into
`~/.codex/hooks.json` and does not trust them. Codex requires a one-time `/hooks`
review. The end-to-end test uses `--dangerously-bypass-hook-trust` only because it is
an automated disposable test; normal users must review the exact hooks.

## Memory semantics

- Explicit `Remember this: ...` is stored as `verified` with source `user`.
- The `Stop` handoff defaults to `unverified`, confidence `0.6`; it becomes
  `verified`, confidence `0.9`, only with linked transcript evidence.
- Raw transcripts, raw tool output, credentials, customer email addresses, and
  oversized writes are not stored by the runtime.
- Current repository state overrides recalled memory.
- `Forget ...` is a two-step, confirmation-gated deletion; it is not silent deletion.

## Maintenance checks

The current repository checks validate sixteen skills and local links, pass 161 unit
tests, and build a reproducible 183-file archive. The Codex verification used a
disposable home, project, Engram data directory, and session; no user memory data or
credentials were copied into the repository.

## Limits

- One Codex version, model, and run; no statistical significance.
- Handoffs are verified only when a verification command and success marker are
  linked to the transcript; otherwise they remain unverified.
- `forget` is a two-step, confirmation-gated deletion, not a single-command erase.
- DSH lifecycle hooks and live delivery are verified; its handoff is conditional like
  Codex and remains unverified without transcript evidence.
- Claude hooks are configuration-tested; no Claude binary/auth was available for a live run.
- The e2e test bypasses hook trust; the normal `/hooks` review remains a manual setup
  step.
- The runtime depends on Engram's project config (`.engram/config.json`); a repository
  without it is intentionally skipped.

## Reproduction

```sh
python scripts/install_codex_adapter.py check --codex-home "$HOME/.codex"
python scripts/verify_codex_adapter.py \
  --engram-bin /path/to/engram \
  --artifacts .agents/artifacts/codex-verification
```

Full unit coverage is in `tests/test_codex_adapter.py` and
`tests/test_codex_evidence.py`.
