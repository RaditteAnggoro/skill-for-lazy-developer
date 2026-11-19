"""Export, verify, import, back up, and roll back the portable skill pack.

The pack is host-neutral: Markdown skills, the consuming snippet, adapter docs, and
license notices. Host lifecycle hooks remain in their own adapters.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile
import zipfile


FORMAT = 1
MANIFEST = "manifest.json"
PACK_PATHS = (
    ".agents/skills",
    "AGENTS.snippet.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "VERSION",
    "adapters",
    "docs/ADAPTERS.md",
    "docs/SOURCES.md",
)
ROLE_PATH = ".agents/roles"
IMPORT_ROOTS = (".agents/skills",)
IMPORT_FILES = ("AGENTS.snippet.md",)


class PackError(RuntimeError):
    pass


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _collect(root, include_roles=False):
    root = Path(root).resolve()
    files = {}
    paths = PACK_PATHS + ((ROLE_PATH,) if include_roles else ())
    for relative in paths:
        path = root / relative
        if not path.exists():
            raise PackError("missing pack path: {}".format(relative))
        candidates = path.rglob("*") if path.is_dir() else [path]
        for candidate in candidates:
            if not candidate.is_file() or candidate.is_symlink():
                continue
            rel = candidate.relative_to(root).as_posix()
            files[rel] = candidate.read_bytes()
    return files


def export_pack(root, output, include_roles=False):
    root = Path(root).resolve()
    output = Path(output)
    files = _collect(root, include_roles=include_roles)
    skills = sorted(
        Path(rel).parts[2]
        for rel in files
        if rel.startswith(".agents/skills/") and len(Path(rel).parts) >= 4 and Path(rel).name == "SKILL.md"
    )
    manifest = {
        "format": FORMAT,
        "version": (root / "VERSION").read_text(encoding="utf-8").strip(),
        "skills": skills,
        "features": ["roles"] if include_roles else [],
        "roles": sorted(
            Path(rel).stem for rel in files
            if rel.startswith(ROLE_PATH + "/") and rel.endswith(".yaml") and Path(rel).name != "schema.yaml"
        ) if include_roles else [],
        "files": {rel: _sha256(data) for rel, data in sorted(files.items())},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest_info = zipfile.ZipInfo(MANIFEST, date_time=(1980, 1, 1, 0, 0, 0))
        manifest_info.compress_type = zipfile.ZIP_DEFLATED
        manifest_info.external_attr = 0o100644 << 16
        archive.writestr(manifest_info, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        for rel, data in sorted(files.items()):
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    digest = _sha256(output.read_bytes())
    checksum = output.with_name(output.name + ".sha256")
    checksum.write_text("{}  {}\n".format(digest, output.name), encoding="utf-8")
    return {"archive": str(output), "checksum": str(checksum), "skills": skills, "files": len(files), "digest": digest}


def _safe_name(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise PackError("unsafe archive path: {}".format(name))
    return path.as_posix()


def verify_pack(archive):
    archive = Path(archive)
    try:
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
            if len(names) != len(set(names)):
                raise PackError("archive contains duplicate members")
            for name in names:
                _safe_name(name)
            if MANIFEST not in names:
                raise PackError("archive is missing {}".format(MANIFEST))
            try:
                manifest = json.loads(bundle.read(MANIFEST).decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise PackError("invalid manifest: {}".format(exc))
            if manifest.get("format") != FORMAT:
                raise PackError("unsupported pack format")
            files = manifest.get("files")
            if not isinstance(files, dict):
                raise PackError("manifest files must be an object")
            expected = set(files) | {MANIFEST}
            if set(names) != expected:
                raise PackError("archive members do not match manifest")
            for name in names:
                if name == MANIFEST:
                    continue
                if _sha256(bundle.read(name)) != files[name]:
                    raise PackError("checksum mismatch for {}".format(name))
    except zipfile.BadZipFile as exc:
        raise PackError("invalid zip: {}".format(exc))
    return manifest


def import_pack(archive, target, apply=False, include_roles=False):
    manifest = verify_pack(archive)
    target = Path(target).resolve()
    if not target.is_dir():
        raise PackError("target must be an existing directory: {}".format(target))
    plan = []
    with zipfile.ZipFile(archive) as bundle:
        for name in manifest["files"]:
            if name.startswith(".agents/skills/"):
                parts = PurePosixPath(name).parts
                if len(parts) >= 3:
                    plan.append("/".join(parts[:3]))
            elif include_roles and "roles" in manifest.get("features", []) and name.startswith(ROLE_PATH + "/"):
                plan.append(ROLE_PATH)
            elif name in IMPORT_FILES:
                plan.append(name)
    unique = sorted(set(plan))
    if not apply:
        return {"target": str(target), "apply": False, "files": unique, "skills": manifest.get("skills", [])}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = target / ".agents" / "backups" / ("skill-pack-" + stamp)
    counter = 1
    while backup.exists():
        backup = target / ".agents" / "backups" / ("skill-pack-{}-{}".format(stamp, counter))
        counter += 1
    backup.mkdir(parents=True)
    selected = []
    with zipfile.ZipFile(archive) as bundle:
        for name in manifest["files"]:
            if include_roles and "roles" in manifest.get("features", []) and name.startswith(ROLE_PATH + "/"):
                pass
            elif not name.startswith(".agents/skills/") and name not in IMPORT_FILES:
                continue
            selected.append(name)
    saved = []
    for name in selected:
        destination = target / name
        if not destination.resolve().is_relative_to(target):
            raise PackError("import path escapes target: {}".format(name))
        if destination.exists() or destination.is_symlink():
            if destination.is_dir():
                saved.append({"path": name, "backup": str(backup / name)})
                (backup / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(destination, backup / name)
            else:
                saved.append({"path": name, "backup": str(backup / name)})
                (backup / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup / name)
    journal = {"format": FORMAT, "status": "prepared", "saved": saved,
               "planned_files": sorted(selected), "imported_files": []}
    (backup / "manifest.json").write_text(json.dumps(journal, indent=2) + "\n", encoding="utf-8")
    with zipfile.ZipFile(archive) as bundle:
        for name in selected:
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(bundle.read(name))
            journal["imported_files"].append(name)
            (backup / "manifest.json").write_text(json.dumps(journal, indent=2) + "\n", encoding="utf-8")
    journal["status"] = "complete"
    (backup / "manifest.json").write_text(json.dumps(journal, indent=2) + "\n", encoding="utf-8")
    return {"target": str(target), "apply": True, "backup": str(backup), "files": unique, "skills": manifest.get("skills", [])}


def rollback(backup, target):
    backup = Path(backup).resolve()
    target = Path(target).resolve()
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    imported = manifest.get("imported_files")
    if imported is None:
        if manifest.get("status") == "prepared":
            imported = manifest.get("planned_files", [])
        else:
            raise PackError("legacy backup cannot be rolled back safely; restore saved files manually")
    elif not imported and manifest.get("status") == "prepared":
        imported = manifest.get("planned_files", [])
    for name in imported:
        _safe_name(name)
        path = target / name
        if path.is_file() or path.is_symlink():
            path.unlink()
    for item in manifest.get("saved", []):
        source = Path(item["backup"])
        destination = target / item["path"]
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    return {"target": str(target), "restored": len(manifest.get("saved", [])), "removed": len(manifest.get("imported", []))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export")
    export.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--with-roles", action="store_true")
    verify = sub.add_parser("verify")
    verify.add_argument("archive", type=Path)
    verify.add_argument("--json", action="store_true")
    imp = sub.add_parser("import")
    imp.add_argument("archive", type=Path)
    imp.add_argument("--target", type=Path, required=True)
    imp.add_argument("--apply", action="store_true")
    imp.add_argument("--with-roles", action="store_true")
    imp.add_argument("--json", action="store_true")
    roll = sub.add_parser("rollback")
    roll.add_argument("--backup", type=Path, required=True)
    roll.add_argument("--target", type=Path, required=True)
    roll.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            result = export_pack(args.root, args.output, include_roles=args.with_roles)
        elif args.command == "verify":
            result = verify_pack(args.archive)
        elif args.command == "import":
            result = import_pack(args.archive, args.target, apply=args.apply, include_roles=args.with_roles)
        else:
            result = rollback(args.backup, args.target)
    except (OSError, PackError, ValueError, json.JSONDecodeError) as exc:
        print("pack failed: {}".format(exc), file=sys.stderr)
        return 1
    if getattr(args, "json", False) or args.command == "export":
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
