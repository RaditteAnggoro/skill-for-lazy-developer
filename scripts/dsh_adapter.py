"""Install and verify the DSH adapter for this skill pack.

DSH already discovers project skills from ``.agents/skills`` and reads ``AGENTS.md``.
This adapter adds the DSH-specific routing calibration and makes the merge
inspectable, idempotent, and reversible.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "AGENTS.snippet.md"
OVERLAY = ROOT / "adapters/dsh/AGENTS.dsh.md"
START = "<!-- codex-developer-skills:dsh:start -->"
END = "<!-- codex-developer-skills:dsh:end -->"
EXPECTED_SKILLS = (
    "adaptive-workflow",
    "architecture-map",
    "browser-diagnostics",
    "feature-discovery",
    "lean-senior-engineering",
    "release-readiness",
    "research-plan-implement",
    "systematic-debugging",
    "verification-before-completion",
)
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---(?:\n|$)", re.DOTALL)


class AdapterError(RuntimeError):
    pass


def _frontmatter(text):
    match = FRONTMATTER.match(text)
    if match is None:
        raise AdapterError("SKILL.md must start with YAML frontmatter")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise AdapterError("SKILL.md frontmatter must be a mapping")
    return data


def discover_skills(root):
    skills_root = Path(root) / ".agents/skills"
    if not skills_root.is_dir():
        raise AdapterError("missing .agents/skills directory")
    names = []
    errors = []
    for directory in sorted(skills_root.iterdir()):
        if not directory.is_dir():
            continue
        entry = directory / "SKILL.md"
        if not entry.is_file():
            continue
        try:
            metadata = _frontmatter(entry.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError, AdapterError) as exc:
            errors.append("{}: {}".format(directory.name, exc))
            continue
        name = metadata.get("name")
        description = metadata.get("description")
        if name != directory.name:
            errors.append("{}: frontmatter name does not match directory".format(directory.name))
        if not isinstance(description, str) or not description.strip():
            errors.append("{}: description is missing".format(directory.name))
        names.append(directory.name)
    return names, errors


def _normalize(text):
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").splitlines()).strip()


def expected_block():
    if not BASE.is_file():
        raise AdapterError("missing shared AGENTS.snippet.md")
    if not OVERLAY.is_file():
        raise AdapterError("missing adapters/dsh/AGENTS.dsh.md")
    return "{}\n\n{}\n{}\n".format(
        START,
        _normalize(BASE.read_text(encoding="utf-8")),
        _normalize(OVERLAY.read_text(encoding="utf-8")),
    ) + END


def block_state(text, expected):
    starts = text.count(START)
    ends = text.count(END)
    if starts == 0 and ends == 0:
        return "missing"
    if starts != 1 or ends != 1:
        return "malformed"
    start = text.index(START)
    end = text.index(END) + len(END)
    actual = _normalize(text[start:end])
    return "current" if actual == _normalize(expected) else "outdated"


def _skill_errors(root):
    names, errors = discover_skills(root)
    missing = sorted(set(EXPECTED_SKILLS) - set(names))
    if missing:
        errors.append("missing skills: {}".format(", ".join(missing)))
    return names, errors


def check_project(root):
    root = Path(root).resolve()
    errors = []
    names, skill_errors = _skill_errors(root)
    errors.extend(skill_errors)
    instructions = root / "AGENTS.md"
    state = "missing"
    if instructions.is_file():
        try:
            state = block_state(
                instructions.read_text(encoding="utf-8"), expected_block()
            )
        except (OSError, UnicodeError, AdapterError) as exc:
            errors.append("AGENTS.md: {}".format(exc))
    else:
        errors.append("missing AGENTS.md")
    if state != "current":
        errors.append("DSH instruction block is {}".format(state))
    return {
        "root": str(root),
        "skills": names,
        "skill_count": len(names),
        "block": state,
        "errors": errors,
        "ok": not errors,
    }


def _backup(path):
    if not path.exists():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(path.name + ".codex-skills-backup-" + stamp)
    counter = 1
    while backup.exists():
        backup = path.with_name(
            path.name + ".codex-skills-backup-{}-{}".format(stamp, counter)
        )
        counter += 1
    shutil.copy2(path, backup)
    return backup


def install(root, dry_run=False):
    root = Path(root).resolve()
    _, skill_errors = _skill_errors(root)
    if skill_errors:
        raise AdapterError("; ".join(skill_errors))
    instructions = root / "AGENTS.md"
    expected = expected_block()
    current = instructions.read_text(encoding="utf-8") if instructions.exists() else ""
    current_state = block_state(current, expected) if instructions.exists() else "missing"
    if current_state == "current":
        return {"changed": False, "backup": None, "state": "current"}
    if current_state == "malformed":
        raise AdapterError("AGENTS.md contains a partial or duplicate DSH block")
    if dry_run:
        return {"changed": True, "backup": None, "state": current_state, "dry_run": True}

    backup = _backup(instructions)
    if current_state == "missing":
        updated = current
        if updated and not updated.endswith("\n"):
            updated += "\n"
        if updated and not updated.endswith("\n\n"):
            updated += "\n"
        updated += expected
    else:
        start = current.index(START)
        end = current.index(END) + len(END)
        updated = current[:start] + expected + current[end:]
    instructions.write_text(updated, encoding="utf-8")
    return {
        "changed": True,
        "backup": str(backup) if backup else None,
        "state": "installed",
    }


def uninstall(root, dry_run=False):
    root = Path(root).resolve()
    instructions = root / "AGENTS.md"
    if not instructions.is_file():
        return {"changed": False, "backup": None}
    current = instructions.read_text(encoding="utf-8")
    if START not in current and END not in current:
        return {"changed": False, "backup": None}
    if current.count(START) != 1 or current.count(END) != 1:
        raise AdapterError("AGENTS.md contains a partial or duplicate DSH block")
    if dry_run:
        return {"changed": True, "backup": None, "dry_run": True}
    backup = _backup(instructions)
    start = current.index(START)
    end = current.index(END) + len(END)
    updated = (current[:start].rstrip() + "\n" + current[end:].lstrip()).strip()
    if updated:
        updated += "\n"
    instructions.write_text(updated, encoding="utf-8")
    return {"changed": True, "backup": str(backup) if backup else None}


def rollback(root, backup):
    root = Path(root).resolve()
    backup = Path(backup).resolve()
    try:
        backup.relative_to(root)
    except ValueError:
        raise AdapterError("backup must be inside the project root")
    if backup.name == "AGENTS.md" or not backup.is_file():
        raise AdapterError("backup is not a valid AGENTS.md backup")
    target = root / "AGENTS.md"
    shutil.copy2(backup, target)
    return {"restored": str(target), "backup": str(backup)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "install", "uninstall"):
        command = subparsers.add_parser(name)
        command.add_argument("--root", type=Path, default=Path.cwd())
        command.add_argument("--json", action="store_true")
        if name != "check":
            command.add_argument("--dry-run", action="store_true")
    rollback_parser = subparsers.add_parser("rollback")
    rollback_parser.add_argument("--root", type=Path, default=Path.cwd())
    rollback_parser.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "check":
            result = check_project(args.root)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif result["ok"]:
                print(
                    "DSH adapter ready: {} skills; AGENTS.md block current.".format(
                        result["skill_count"]
                    )
                )
            else:
                for error in result["errors"]:
                    print("FAIL " + error, file=sys.stderr)
            return 0 if result["ok"] else 1
        if args.command == "install":
            result = install(args.root, dry_run=args.dry_run)
        elif args.command == "uninstall":
            result = uninstall(args.root, dry_run=args.dry_run)
        else:
            result = rollback(args.root, args.backup)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False))
        return 0
    except (AdapterError, OSError, UnicodeError) as exc:
        print("DSH adapter failed: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
