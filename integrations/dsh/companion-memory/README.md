# DSH companion memory bundle

This local DSH bundle connects the Engram MCP server, adds a pre-write privacy
guard, and installs DSH lifecycle hooks for automatic recall, ordinary-language
controls, and a bounded handoff.

## Contents

- `engram-mcp`: a `@deepseek-ai/dsh-mcp-client` row running
  `engram mcp --tools=agent,admin`;
- `engram-guard`: a Host plugin that adds a short memory policy, blocks obvious
  sensitive writes, recalls project context on `agent/created`, handles remember/show/
  opt-out/forget in `agent/pre-step`, and writes a bounded unverified handoff on
  `agent/turn-stopping`;
- `failOnStartupError: false`: missing Engram must not block ordinary work.

The bundle assumes Engram is already installed and available as `engram` on `PATH`.
It does not download or configure Engram.

## Install

```sh
dsh plugin --profile <profile> add /absolute/path/to/integrations/dsh/companion-memory
```

Installing a bundle executes code in the DSH Host process. Review this directory and
use DSH's approval/Full-access flow deliberately.

Verify the rows:

```sh
dsh --profile <profile> --dump-config | grep -E 'engram-(mcp|guard)'
```

The model-facing tools are named `mcp__engram__mem_context`,
`mcp__engram__mem_search`, `mcp__engram__mem_save`, and related Engram tools.

## Privacy boundary

Direct Engram MCP storage accepted the synthetic canary used by the verifier. The Host
guard is therefore **required** for this adapter: it rejects obvious API keys, GitHub
and AWS credentials, private keys, bearer tokens, secret assignments, email addresses,
content over 4,000 characters, and raw prompt capture before write calls reach
Engram.

This guard is pattern-based and does not replace the contract validator, user review,
or provider-side controls.

## Uninstall

```sh
dsh plugin --profile <profile> remove @local/dsh-companion-memory
```

The removal is handled by DSH/pnpm. The package does not write files outside its own
profile installation.

## Lifecycle and controls

The Host plugin uses DSH's public agent lifecycle:

- recall is injected after `agent/created` and before the first model step;
- explicit `Remember this: ...` is stored as a verified user note;
- `Show what you remember` recalls on demand;
- `Do not remember this project` writes a project opt-out;
- `Forget ...` is advisory and requires confirmation;
- `agent/turn-stopping` stores a bounded **unverified** handoff.

The lifecycle behavior is covered by `test_lifecycle.mjs` and a live disposable DSH
run. The live run passed recall, remember, handoff, opt-out, fail-open, and uninstall.
An earlier attempt failed because the injected context lacked a complete message
identity; recall now has an identified message and is added during `agent/pre-step`,
when the real user prompt is present.

## Limitations

- Automatic recall and handoff are wired and live-verified.
- The handoff is unverified.
- `forget` is advisory, not an automatic deletion flow.
- The guard checks write arguments, not provider logs, backups, or remote copies.
- This bundle was verified against Engram 3.6.2 and a local DSH profile; re-run the
  verifier after upgrading either.
