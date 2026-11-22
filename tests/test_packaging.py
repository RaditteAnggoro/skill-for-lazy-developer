import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from scripts.build_release import PATHS, build_release, collect_files


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        for name in PATHS[:5]:
            (self.root / name).mkdir(parents=True)
        for name in PATHS[5:]:
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            (self.root / name).write_text("example\n", encoding="utf-8")
        (self.root / "VERSION").write_text("0.1.0\n")
        sample = self.root / ".agents/skills/example/SKILL.md"
        sample.parent.mkdir(parents=True)
        sample.write_text("example skill\n")

    def test_distribution_includes_host_adapter_directories(self):
        self.assertIn("adapters", PATHS)
        self.assertIn("integrations", PATHS)

    def test_archive_includes_hidden_skills_and_checksum(self):
        archive, checksum, count = build_release(self.root)
        with ZipFile(archive) as bundle:
            self.assertIn("codex-developer-skills-0.1.0/.agents/skills/example/SKILL.md", bundle.namelist())
            self.assertEqual(len(bundle.namelist()), count)
            self.assertIsNone(bundle.testzip())
        expected = hashlib.sha256(archive.read_bytes()).hexdigest()
        self.assertEqual(checksum.read_text().split()[0], expected)

    def test_archive_has_deterministic_build_info(self):
        archive, _, _ = build_release(self.root)
        with ZipFile(archive) as bundle:
            info = json.loads(bundle.read("codex-developer-skills-0.1.0/BUILD-INFO.json"))
        self.assertEqual(info["version"], "0.1.0")
        self.assertIn("commit", info)
        self.assertFalse(info["clean_snapshot"])

    def test_excludes_local_and_sensitive_files(self):
        for name in (".git/config", ".venv/lib/local.py", ".agents/artifacts/task/private.md", "docs/.DS_Store", "scripts/__pycache__/cache.pyc", "docs/.env", "docs/token.key"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("not distributable\n")
        files = [path.relative_to(self.root).as_posix() for path in collect_files(self.root)]
        self.assertFalse(any(".git/" in name or ".venv/" in name or "artifacts/" in name for name in files))
        self.assertNotIn("docs/.DS_Store", files)
        self.assertNotIn("scripts/__pycache__/cache.pyc", files)
        self.assertNotIn("docs/.env", files)
        self.assertNotIn("docs/token.key", files)

    def test_require_clean_rejects_non_git_or_dirty_snapshot(self):
        with self.assertRaisesRegex(ValueError, "clean source snapshot"):
            build_release(self.root, require_clean=True)

    @unittest.skipUnless(shutil.which("git"), "git unavailable")
    def test_clean_archive_excludes_ignored_untracked_files_inside_allowlist(self):
        # A clean Git status can still conceal local drafts and evidence.
        for relative in PATHS[:5]:
            (self.root / relative / "fixture.txt").write_text("committed fixture\n")
        (self.root / ".gitignore").write_text("docs/private-review.md\n")
        git = ["git", "-C", str(self.root)]
        subprocess.run(git + ["init", "-q"], check=True)
        subprocess.run(git + ["add", "."], check=True)
        subprocess.run(git + ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                              "-c", "commit.gpgsign=false", "commit", "-qm", "fixture"], check=True)
        (self.root / "docs/private-review.md").write_text("synthetic private marker\n")
        subprocess.run(git + ["update-index", "--assume-unchanged", "docs/fixture.txt"], check=True)
        (self.root / "docs/fixture.txt").write_text("local-only edit\n")
        archive, _, _ = build_release(self.root, require_clean=True)
        with ZipFile(archive) as bundle:
            self.assertEqual(bundle.read("codex-developer-skills-0.1.0/docs/fixture.txt"), b"committed fixture\n")
            self.assertNotIn("codex-developer-skills-0.1.0/docs/private-review.md", bundle.namelist())

    def test_archive_is_reproducible(self):
        first, _, _ = build_release(self.root)
        data = first.read_bytes()
        second, _, _ = build_release(self.root)
        self.assertEqual(data, second.read_bytes())

    def test_rejects_invalid_version(self):
        (self.root / "VERSION").write_text("../outside\n")
        with self.assertRaisesRegex(ValueError, "VERSION"):
            build_release(self.root)

    def test_rejects_missing_distribution_file(self):
        (self.root / "LICENSE").unlink()
        with self.assertRaisesRegex(ValueError, "missing distribution path"):
            collect_files(self.root)

    def test_rejects_symlink_source(self):
        target = self.root / "docs/guide.md"
        target.write_text("guide\n")
        try:
            (self.root / "docs/alias.md").symlink_to(target)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaisesRegex(ValueError, "symlink"):
            collect_files(self.root)


if __name__ == "__main__":
    unittest.main()
