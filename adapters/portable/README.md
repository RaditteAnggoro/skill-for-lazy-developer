# Portable adapter layer

Use the portable pack when the target host can discover `.agents/skills/` and read the
shared `AGENTS.snippet.md`:

```sh
python scripts/package_skill_pack.py export --output dist/skill-pack.zip
python scripts/package_skill_pack.py import dist/skill-pack.zip --target /path/to/project
```

This layer contains instructions and skill metadata only. Host-specific hooks, memory,
MCP configuration, and user-level settings remain in the Codex, Claude, and DSH adapters.
See [docs/PORTABLE_PACK.md](../../docs/PORTABLE_PACK.md) for verification, backup, and
rollback commands.
