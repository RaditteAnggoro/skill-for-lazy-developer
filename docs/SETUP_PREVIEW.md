# Setup and import preview

Before importing the skill pack, run a read-only preview that lists what would be copied,
what conflicts, what is optional, and which host/tool dependencies are missing.

```sh
python scripts/agent_setup_preview.py --target /path/to/project
python scripts/agent_setup_preview.py --target /path/to/project --with-roles
python scripts/agent_setup_preview.py --target /path/to/project --with-memory --with-ui
```

The preview does **not** install or modify anything. No files are modified. Secrets and credentials are never imported. It reports:

- skills and `AGENTS.snippet.md` that would be imported;
- optional role contracts;
- existing skill-name conflicts (the real import will back them up);
- skipped host-specific files such as `CLAUDE.md`;
- required/optional support such as Python, Engram, Node, Chrome, Playwright, and
  agent host CLIs;
- installed wrappers and role directories;
- the explicit rule that credentials, `.env`, API keys, and Authorization headers are
  never imported.

`--strict` exits nonzero only when a **requested** requirement is missing, for example
`--with-memory` without an Engram binary. `--json` emits machine-readable output.

This is a preflight, not an installer. After reviewing it, use the portable-pack
dry-run/import flow in [PORTABLE_PACK.md](PORTABLE_PACK.md). If the target has an
existing `AGENTS.md`, merge the snippet manually; the importer does not overwrite it.

No agent host, MCP, browser driver, package manager, or database is installed by this
command. The user decides which optional capabilities to enable.
