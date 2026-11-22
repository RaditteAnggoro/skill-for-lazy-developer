# Portable skill pack

The portable pack moves the host-neutral skill layer between projects without copying
host lifecycle hooks or credentials. It is intended for Codex, DSH, Claude projects, and
plain repositories that can read `.agents/skills/`.

## What is included

- all `.agents/skills/*/SKILL.md` and UI metadata;
- `AGENTS.snippet.md`;
- adapter documentation and license notices;
- `VERSION` and a canonical `manifest.json`.

The manifest records every file hash, the pack format, and the skill names. A sibling
`.sha256` file records the archive digest. Role contracts are **optional**:

```sh
python scripts/package_skill_pack.py export --output dist/skill-pack.zip --with-roles
python scripts/package_skill_pack.py import dist/skill-pack.zip --target /path/to/project --with-roles
```

Without `--with-roles`, the default pack and import behave exactly as before.

## Preview first

```sh
python scripts/agent_setup_preview.py --target /path/to/project
python scripts/agent_setup_preview.py --target /path/to/project --with-roles --with-memory --with-ui
```

The preview lists conflicts, skipped host-specific files, required/optional apps and
plugins, and the fact that credentials are never imported. It does not modify the
target. See [SETUP_PREVIEW.md](SETUP_PREVIEW.md).

## Export

```sh
python scripts/package_skill_pack.py export --output dist/skill-pack.zip
python scripts/package_skill_pack.py verify dist/skill-pack.zip
```

The archive is deterministic for the same source tree: fixed timestamps, sorted entries,
and manifest hashes.

## Import

Preview first:

```sh
python scripts/package_skill_pack.py import dist/skill-pack.zip --target /path/to/project
```

Apply after reviewing the plan:

```sh
python scripts/package_skill_pack.py import dist/skill-pack.zip \
  --target /path/to/project --apply
```

Import installs each skill by name and updates `AGENTS.snippet.md`. It does not delete
unrelated skills and does not modify `AGENTS.md`, hooks, or host configuration. Existing
targets are copied to `.agents/backups/skill-pack-<timestamp>/` before replacement.

## Recovery

The apply result prints the backup directory. Roll back with:

```sh
python scripts/package_skill_pack.py rollback \
  --backup /path/to/project/.agents/backups/skill-pack-<timestamp> \
  --target /path/to/project
```

Rollback compares the current file digests with the installed and original contents.
It restores only paths the import changed and stops before restoring files if a user
edit conflicts. The prepared journal also supports recovery after an interrupted
import. Older journals without digests require manual recovery from the saved files.
Keep the backup until the project has been checked.

## Safety boundaries

- The importer verifies the manifest hash for every member and rejects duplicate,
  absolute, or traversal paths.
- The pack does not install packages, run hooks, trust hooks, or copy credentials.
- Host lifecycle installers remain separate and require their own review/approval.
- A passing import proves file integrity, not skill quality or host behavior.
