"""Build a deterministic source archive from an explicit distribution allowlist."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED


PATHS = (
    ".agents/skills", ".agents/roles", ".github", "docs", "scripts", "tests",
    "adapters", "integrations", ".codex", ".claude", ".codex-plugin/plugin.json",
    "AGENTS.md", "AGENTS.snippet.md", "README.md", "LICENSE", "NOTICE.md",
    "THIRD_PARTY_NOTICES.md", "CITATION.cff", "VERSION",
    "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", ".gitignore",
    ".gitattributes", "requirements-dev.txt",
)
EXCLUDED = {
    ".git", ".venv", "venv", "__pycache__", ".DS_Store", "Thumbs.db",
    "node_modules", ".next", "dist", "artifacts", ".npm-cache",
}


def collect_files(root):
    root = root.resolve()
    files = []
    for relative in PATHS:
        path = root / relative
        if not path.exists():
            raise ValueError("missing distribution path: {}".format(relative))
        try:
            path.resolve().relative_to(root)
        except ValueError:
            raise ValueError("distribution path escapes repository: {}".format(relative))
        if path.is_symlink():
            raise ValueError("distribution contains a symlink: {}".format(relative))
        candidates = path.rglob("*") if path.is_dir() else [path]
        for candidate in candidates:
            parts = candidate.relative_to(root).parts
            if any(part in EXCLUDED for part in parts):
                continue
            if candidate.is_symlink():
                raise ValueError("distribution contains a symlink: {}".format(candidate.relative_to(root)))
            if not candidate.is_file():
                continue
            if candidate.name.startswith(".env") or candidate.suffix in {".key", ".pem", ".pyc"}:
                continue
            files.append(candidate)
    return sorted(set(files))


def build_release(root, require_clean=False):
    root = root.resolve()
    if require_clean:
        try:
            status = subprocess.run(["git", "-C", str(root), "status", "--porcelain"], capture_output=True, text=True, check=False)
        except OSError as exc:
            raise ValueError("cannot verify clean source snapshot: {}".format(exc))
        if status.returncode != 0 or status.stdout.strip():
            raise ValueError("source snapshot is not clean; commit or remove local changes before publishing")
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None:
        raise ValueError("VERSION must use MAJOR.MINOR.PATCH")
    files = collect_files(root)
    try:
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=False,
        ).stdout.strip() or None
    except OSError:
        commit = None
    build_info = {
        "schema_version": 1,
        "version": version,
        "commit": commit,
        "clean_snapshot": bool(require_clean and commit),
        "files": len(files),
    }
    output = root / "dist"
    if output.is_symlink():
        raise ValueError("dist must not be a symlink")
    output.mkdir(exist_ok=True)
    stem = "codex-developer-skills-" + version
    archive = output / (stem + ".zip")
    checksum = output / (stem + ".zip.sha256")
    if archive.is_symlink() or checksum.is_symlink():
        raise ValueError("distribution output must not be a symlink")
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
        info = ZipInfo(stem + "/BUILD-INFO.json", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = ZIP_DEFLATED
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        bundle.writestr(info, json.dumps(build_info, indent=2, sort_keys=True) + "\n")
        for source in files:
            name = stem + "/" + source.relative_to(root).as_posix()
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, source.read_bytes())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum.write_text(digest + "  " + archive.name + "\n", encoding="utf-8")
    return archive, checksum, len(files) + 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    try:
        archive, checksum, count = build_release(args.root, require_clean=args.require_clean)
    except (OSError, ValueError) as exc:
        print("Build failed: {}".format(exc), file=sys.stderr)
        return 1
    print("Built {} ({} files)".format(archive.name, count))
    print("Checksum: {}".format(checksum.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
