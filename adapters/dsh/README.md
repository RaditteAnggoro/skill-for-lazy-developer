# DSH skill adapter

DeepSeek Harness (DSH) discovers project skills from `.agents/skills` when its
`dsh-skill-filesystem` plugin is mounted, and reads `AGENTS.md` through
`dsh-agent-instructions`. This adapter adds DSH-specific routing calibration and a
safe, repeatable merge of the shared instructions.

## Check

```sh
python scripts/dsh_adapter.py check --root .
```

The check requires the nine workflow directories, valid frontmatter, and one current
marked block in `AGENTS.md`. It changes nothing.

## Install

```sh
python scripts/dsh_adapter.py install --root . --dry-run
python scripts/dsh_adapter.py install --root .
```

The installer:

- reads `AGENTS.snippet.md` and `adapters/dsh/AGENTS.dsh.md`;
- writes one block between `<!-- codex-developer-skills:dsh:start -->` and
  `<!-- codex-developer-skills:dsh:end -->`;
- backs up an existing `AGENTS.md`;
- is idempotent and leaves unrelated instructions untouched.

## Uninstall and rollback

```sh
python scripts/dsh_adapter.py uninstall --root .
python scripts/dsh_adapter.py rollback --root . --backup <backup-file>
```

`uninstall` removes only the managed block. `rollback` restores a backup created by the
installer. Backups stay inside the project.

## Requirements

- A DSH profile with `@deepseek-ai/dsh-skill`, `@deepseek-ai/dsh-skill-filesystem`,
  `@deepseek-ai/dsh-tool-skill`, and `@deepseek-ai/dsh-agent-instructions` mounted.
- Project root marked by `.git`, or the working directory when no marker is present.
- No OpenAI-specific `agents/openai.yaml` assumption; DSH ignores it.

The DSH memory runtime is a separate bundle under
[`integrations/dsh/companion-memory`](../../integrations/dsh/companion-memory).
