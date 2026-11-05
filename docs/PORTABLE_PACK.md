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
`.sha256` file records the archive digest.

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

Rollback removes the imported paths and restores the saved files. Keep the backup until
the project has been checked.

## Safety boundaries

- The importer verifies the manifest hash for every member and rejects duplicate,
  absolute, or traversal paths.
- The pack does not install packages, run hooks, trust hooks, or copy credentials.
- Host lifecycle installers remain separate and require their own review/approval.
- A passing import proves file integrity, not skill quality or host behavior.
