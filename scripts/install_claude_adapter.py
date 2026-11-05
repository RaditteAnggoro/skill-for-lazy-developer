"""Install, inspect, and remove the Claude Code memory lifecycle adapter.

Claude Code hooks are command handlers in a settings JSON file. This installer
only edits the user-level settings file and a private companion-memory directory,
keeps backups, and never touches project files except by checking an optional
Engram project config.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SOURCE = ROOT / "integrations/codex/memory_runtime.py"
MARKER = "companion-memory/memory_runtime.py"
EVENTS = {
    "SessionStart": ("session-start", 10, "Recalling project memory", "startup|resume|clear|compact|fork"),
    "UserPromptSubmit": ("user-prompt", 10, "Checking project memory controls", None),
    "Stop": ("stop", 10, "Saving a bounded session handoff", None),
}


class AdapterError(RuntimeError):
    pass


def claude_home(value=None):
    return Path(value or os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude")).resolve()


def runtime_paths(home):
    runtime_dir = Path(home) / "companion-memory"
    return runtime_dir, runtime_dir / "memory_runtime.py", runtime_dir / "config.json"


def settings_path(home):
    return Path(home) / "settings.json"


def _read_json(path, fallback):
    if not path.is_file():
        return fallback
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdapterError("{}: {}".format(path, exc))
    if not isinstance(data, dict):
        raise AdapterError("{} must contain a JSON object".format(path))
    return data


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def _backup(home, files):
    existing = [path for path in files if path.exists()]
    if not existing:
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = Path(home) / "companion-memory" / "backups" / stamp
    counter = 1
    while destination.exists():
        destination = Path(home) / "companion-memory" / "backups" / "{}-{}".format(stamp, counter)
        counter += 1
    destination.mkdir(parents=True)
    for path in existing:
        shutil.copy2(path, destination / path.name)
    return str(destination)


def _python():
    return shutil.which("python3") or sys.executable


def _command(runtime, subcommand):
    return "{} {} {}".format(shlex.quote(_python()), shlex.quote(str(runtime)), subcommand)


def _our_handler(handler):
    return (
        isinstance(handler, dict)
        and handler.get("type") == "command"
        and isinstance(handler.get("command"), str)
        and MARKER in handler["command"]
    )


def _strip_ours(hooks):
    cleaned = {}
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            raise AdapterError("hooks.{} must be an array".format(event))
        next_groups = []
        for group in groups:
            if not isinstance(group, dict):
                raise AdapterError("hooks.{} contains a non-object group".format(event))
            handlers = group.get("hooks")
            if not isinstance(handlers, list):
                raise AdapterError("hooks.{} group is missing a handlers array".format(event))
            kept = [handler for handler in handlers if not _our_handler(handler)]
            if kept:
                next_groups.append({**group, "hooks": kept})
        if next_groups:
            cleaned[event] = next_groups
    return cleaned


def expected_hooks(home):
    _, runtime, _ = runtime_paths(home)
    result = {}
    for event, (subcommand, timeout, status, matcher) in EVENTS.items():
        group = {"hooks": [{
            "type": "command",
            "command": _command(runtime, subcommand),
            "timeout": timeout,
            "statusMessage": status,
        }]}
        if matcher:
            group["matcher"] = matcher
        result[event] = [group]
    return result


def install(home, engram_bin=None, data_dir=None, dry_run=False):
    home = Path(home).resolve()
    runtime_dir, runtime, config_path = runtime_paths(home)
    if not RUNTIME_SOURCE.is_file():
        raise AdapterError("missing runtime source: {}".format(RUNTIME_SOURCE))
    engram = engram_bin or shutil.which("engram") or "engram"
    config = _read_json(config_path, {})
    config["engram_bin"] = str(engram)
    if data_dir:
        config["data_dir"] = str(Path(data_dir).resolve())
    if "opt_outs" not in config or not isinstance(config["opt_outs"], list):
        config["opt_outs"] = []
    settings_file = settings_path(home)
    settings = _read_json(settings_file, {})
    hooks = settings.get("hooks")
    if hooks is None:
        hooks = {}
    if not isinstance(hooks, dict):
        raise AdapterError("settings.json hooks must be an object")
    cleaned = _strip_ours(hooks)
    for event, groups in expected_hooks(home).items():
        cleaned.setdefault(event, []).extend(groups)
    updated = dict(settings)
    updated["hooks"] = cleaned
    if dry_run:
        return {"changed": True, "dry_run": True, "home": str(home)}
    runtime_current = runtime.is_file() and runtime.read_bytes() == RUNTIME_SOURCE.read_bytes()
    config_current = config_path.is_file() and _read_json(config_path, {}) == config
    if updated == settings and runtime_current and config_current:
        return {"changed": False, "home": str(home), "backup": None, "engram_bin": str(engram)}
    backup = _backup(home, [settings_file, config_path])
    runtime_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RUNTIME_SOURCE, runtime)
    _write_json(config_path, config)
    _write_json(settings_file, updated)
    return {
        "changed": True,
        "home": str(home),
        "backup": backup,
        "engram_bin": str(engram),
        "settings": str(settings_file),
        "runtime": str(runtime),
    }


def check(home, engram_bin=None, project=None):
    home = Path(home).resolve()
    _, runtime, config_path = runtime_paths(home)
    errors = []
    if not runtime.is_file():
        errors.append("missing runtime: {}".format(runtime))
    config = _read_json(config_path, {})
    engram = engram_bin or config.get("engram_bin") or "engram"
    resolved = shutil.which(str(engram)) if not Path(str(engram)).is_absolute() else str(engram)
    if not resolved or not Path(str(resolved)).is_file():
        errors.append("Engram binary not found: {}".format(engram))
    settings = _read_json(settings_path(home), {})
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    if not isinstance(hooks, dict):
        errors.append("settings.json must contain a hooks object")
        hooks = {}
    for event in EVENTS:
        found = 0
        for group in hooks.get(event, []) if isinstance(hooks.get(event, []), list) else []:
            for handler in group.get("hooks", []) if isinstance(group, dict) else []:
                if _our_handler(handler):
                    found += 1
        if found != 1:
            errors.append("{} must have exactly one memory hook (found {})".format(event, found))
    if project:
        project_path = Path(project).resolve()
        if not (project_path / ".engram/config.json").is_file():
            errors.append("project has no .engram/config.json: {}".format(project_path))
    return {
        "home": str(home),
        "runtime": str(runtime),
        "engram_bin": str(engram),
        "ok": not errors,
        "errors": errors,
    }


def uninstall(home, dry_run=False):
    home = Path(home).resolve()
    settings_file = settings_path(home)
    runtime_dir, runtime, config_path = runtime_paths(home)
    settings = _read_json(settings_file, {})
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        raise AdapterError("settings.json must contain a hooks object")
    cleaned = _strip_ours(hooks)
    updated = dict(settings)
    updated["hooks"] = cleaned
    if dry_run:
        return {"changed": True, "dry_run": True, "home": str(home)}
    backup = _backup(home, [settings_file, config_path, runtime])
    if settings_file.exists() or cleaned:
        _write_json(settings_file, updated)
    if runtime.exists():
        runtime.unlink()
    if config_path.exists():
        config_path.unlink()
    try:
        runtime_dir.rmdir()
    except OSError:
        pass
    return {"changed": True, "home": str(home), "backup": backup}


def rollback(home, backup):
    home = Path(home).resolve()
    backup = Path(backup).resolve()
    try:
        backup.relative_to(home)
    except ValueError:
        raise AdapterError("backup must be inside the Claude home")
    if not backup.is_dir():
        raise AdapterError("backup directory not found")
    _, runtime, config_path = runtime_paths(home)
    restored = []
    for name, target in (("settings.json", settings_path(home)), ("config.json", config_path), ("memory_runtime.py", runtime)):
        source = backup / name
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            restored.append(str(target))
    if not restored:
        raise AdapterError("backup contains no adapter files")
    return {"home": str(home), "backup": str(backup), "restored": restored}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "install", "uninstall"):
        command = subparsers.add_parser(name)
        command.add_argument("--claude-home", type=Path)
        command.add_argument("--engram-bin")
        command.add_argument("--json", action="store_true")
        if name == "check":
            command.add_argument("--project", type=Path)
        if name == "install":
            command.add_argument("--data-dir", type=Path)
            command.add_argument("--dry-run", action="store_true")
        if name == "uninstall":
            command.add_argument("--dry-run", action="store_true")
    rollback_parser = subparsers.add_parser("rollback")
    rollback_parser.add_argument("--claude-home", type=Path)
    rollback_parser.add_argument("--backup", type=Path, required=True)
    rollback_parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    home = claude_home(args.claude_home)
    try:
        if args.command == "check":
            result = check(home, args.engram_bin, args.project)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif result["ok"]:
                print("Claude adapter ready in {}.".format(home))
            else:
                for error in result["errors"]:
                    print("FAIL " + error, file=sys.stderr)
            return 0 if result["ok"] else 1
        if args.command == "install":
            result = install(home, args.engram_bin, args.data_dir, args.dry_run)
        elif args.command == "uninstall":
            result = uninstall(home, args.dry_run)
        else:
            result = rollback(home, args.backup)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False))
        return 0
    except (AdapterError, OSError) as exc:
        print("Claude adapter failed: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
