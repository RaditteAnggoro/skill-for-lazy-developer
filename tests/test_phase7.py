from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts.scan_skill_security import scan_path
from scripts.package_skill_pack import (
    PackError,
    export_pack,
    import_pack,
    rollback,
    verify_pack,
)


ROOT = Path(__file__).resolve().parents[1]


class Phase7Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.archive = self.root / "skill-pack.zip"
        self.result = export_pack(ROOT, self.archive)

    def tearDown(self):
        self.temp.cleanup()

    def test_export_is_deterministic_and_verifiable(self):
        first = self.archive.read_bytes()
        self.assertGreaterEqual(len(self.result["skills"]), 16)
        manifest = verify_pack(self.archive)
        self.assertEqual(manifest["version"], (ROOT / "VERSION").read_text(encoding="utf-8").strip())
        second_archive = self.root / "second.zip"
        export_pack(ROOT, second_archive)
        self.assertEqual(first, second_archive.read_bytes())
        self.assertTrue(self.archive.with_name(self.archive.name + ".sha256").is_file())

    def test_import_is_dry_run_then_backs_up_and_rolls_back(self):
        target = self.root / "target"
        (target / ".agents/skills/adaptive-workflow").mkdir(parents=True)
        (target / ".agents/skills/old-skill").mkdir(parents=True)
        (target / ".agents/skills/adaptive-workflow/SKILL.md").write_text("# old adaptive\n", encoding="utf-8")
        (target / ".agents/skills/adaptive-workflow/personal-notes.txt").write_text("keep me", encoding="utf-8")
        (target / ".agents/skills/old-skill/SKILL.md").write_text("# old skill\n", encoding="utf-8")
        (target / "AGENTS.snippet.md").write_text("# old snippet\n", encoding="utf-8")
        dry = import_pack(self.archive, target, apply=False)
        self.assertFalse(dry["apply"])
        self.assertIn("# old adaptive", (target / ".agents/skills/adaptive-workflow/SKILL.md").read_text(encoding="utf-8"))
        applied = import_pack(self.archive, target, apply=True)
        self.assertTrue(Path(applied["backup"]).is_dir())
        self.assertIn("name: adaptive-workflow", (target / ".agents/skills/adaptive-workflow/SKILL.md").read_text(encoding="utf-8"))
        self.assertTrue((target / ".agents/skills/old-skill/SKILL.md").is_file())
        rollback(Path(applied["backup"]), target)
        self.assertEqual("# old adaptive\n", (target / ".agents/skills/adaptive-workflow/SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual("keep me", (target / ".agents/skills/adaptive-workflow/personal-notes.txt").read_text(encoding="utf-8"))
        self.assertEqual("# old snippet\n", (target / "AGENTS.snippet.md").read_text(encoding="utf-8"))
        self.assertTrue((target / ".agents/skills/old-skill/SKILL.md").is_file())

    def test_import_writes_recovery_journal(self):
        target = self.root / "journal-target"
        target.mkdir()
        result = import_pack(self.archive, target, apply=True)
        journal = json.loads((Path(result["backup"]) / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(journal["status"], "complete")
        self.assertTrue(journal["planned_files"])
        self.assertEqual(sorted(journal["planned_files"]), sorted(journal["imported_files"]))

    def test_prepared_journal_can_be_rolled_back_after_interruption(self):
        target = self.root / "interrupted-target"
        target.mkdir()
        result = import_pack(self.archive, target, apply=True)
        backup = Path(result["backup"])
        journal = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
        journal["status"] = "prepared"
        journal["imported_files"] = []
        (backup / "manifest.json").write_text(json.dumps(journal), encoding="utf-8")
        rollback(backup, target)
        self.assertFalse((target / ".agents/skills/adaptive-workflow/SKILL.md").exists())

    def test_rollback_preserves_post_import_edits(self):
        target = self.root / 'edited-target'
        target.mkdir()
        result = import_pack(self.archive, target, apply=True)
        edited = target / 'AGENTS.snippet.md'
        edited.write_text('User edited the snippet.', encoding='utf-8')
        with self.assertRaisesRegex(PackError, 'rollback conflict'):
            rollback(result['backup'], target)
        self.assertEqual(edited.read_text(encoding='utf-8'), 'User edited the snippet.')
        self.assertTrue((target / '.agents/skills/adaptive-workflow/SKILL.md').is_file())

    def test_interrupted_import_recovers_only_paths_that_were_applied(self):
        from scripts import package_skill_pack

        target = self.root / 'partial-target'
        target.mkdir()
        snippet = target / 'AGENTS.snippet.md'
        snippet.write_text('original snippet', encoding='utf-8')
        write = package_skill_pack._atomic_write
        attempt = []

        def interrupt(path, content):
            if path.name != 'manifest.json':
                if attempt:
                    raise OSError('synthetic interruption')
                attempt.append(path)
            return write(path, content)

        with patch.object(package_skill_pack, '_atomic_write', side_effect=interrupt):
            with self.assertRaisesRegex(OSError, 'synthetic interruption'):
                import_pack(self.archive, target, apply=True)
        backup, = (target / '.agents/backups').iterdir()
        self.assertTrue(attempt[0].is_file())
        rollback(backup, target)
        self.assertFalse(attempt[0].exists())
        self.assertEqual(snippet.read_text(encoding='utf-8'), 'original snippet')

    def test_checksum_tamper_is_rejected(self):
        tampered = self.root / "tampered.zip"
        with zipfile.ZipFile(self.archive) as source, zipfile.ZipFile(tampered, "w") as target:
            for name in source.namelist():
                data = source.read(name)
                if name == "AGENTS.snippet.md":
                    data += b"\n# injected after export\n"
                target.writestr(name, data)
        with self.assertRaises(PackError):
            verify_pack(tampered)

    def test_path_traversal_is_rejected(self):
        unsafe = self.root / "unsafe.zip"
        with zipfile.ZipFile(unsafe, "w") as archive:
            archive.writestr("../escape.txt", "no")
            archive.writestr("manifest.json", json.dumps({"format": 1, "files": {}}))
        with self.assertRaises(PackError):
            verify_pack(unsafe)

    def test_codex_plugin_manifest_points_to_packaged_skills(self):
        manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["skills"].startswith("./"))
        skill_root = ROOT / manifest["skills"]
        self.assertTrue((skill_root / "adaptive-workflow/SKILL.md").is_file())
        self.assertTrue(manifest["interface"]["displayName"])

    def test_adapter_installers_expose_uninstall_and_rollback(self):
        for script in ("install_codex_adapter.py", "install_claude_adapter.py", "dsh_adapter.py"):
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / script), "--help"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, (script, completed.stderr))
            combined = completed.stdout.lower()
            self.assertIn("uninstall", combined, script)
            self.assertIn("rollback", combined, script)

    def test_pack_skills_pass_security_triage(self):
        self.assertEqual(scan_path(ROOT / ".agents/skills"), [])

    def test_optional_role_pack_is_opt_in_and_imports_safely(self):
        roles_archive = self.root / "roles.zip"
        export_pack(ROOT, roles_archive, include_roles=True)
        manifest = verify_pack(roles_archive)
        self.assertIn("roles", manifest["features"])
        self.assertEqual(len(manifest["roles"]), 4)
        target = self.root / "role-target"
        target.mkdir()
        dry = import_pack(roles_archive, target, apply=False, include_roles=True)
        self.assertIn(".agents/roles", dry["files"])
        import_pack(roles_archive, target, apply=True, include_roles=True)
        self.assertTrue((target / ".agents/roles/ld-financial-integrity-reviewer.yaml").is_file())
        self.assertTrue((target / ".agents/roles/schema.yaml").is_file())
        plain = self.root / "plain-target"
        plain.mkdir()
        import_pack(self.archive, plain, apply=True)
        self.assertFalse((plain / ".agents/roles").exists())

    def test_optional_role_import_preserves_existing_role_and_rolls_back(self):
        roles_archive = self.root / "roles-collision.zip"
        export_pack(ROOT, roles_archive, include_roles=True)
        target = self.root / "role-collision"
        existing = target / ".agents/roles/ld-financial-integrity-reviewer.yaml"
        existing.parent.mkdir(parents=True)
        existing.write_text("id: custom-role\n", encoding="utf-8")
        applied = import_pack(roles_archive, target, apply=True, include_roles=True)
        self.assertTrue(Path(applied["backup"]).is_dir())
        self.assertNotEqual(existing.read_text(encoding="utf-8"), "id: custom-role\n")
        rollback(Path(applied["backup"]), target)
        self.assertEqual(existing.read_text(encoding="utf-8"), "id: custom-role\n")

    def test_license_inventory_covers_development_tools(self):
        text = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8").lower()
        for name in ("pyyaml", "tiktoken", "playwright-core", "pngjs", "pixelmatch", "react", "vite", "next.js"):
            self.assertIn(name, text)

    def test_phase_seven_evidence(self):
        import yaml
        data = yaml.safe_load((ROOT / "tests/phase7_evidence.yaml").read_text(encoding="utf-8"))
        self.assertTrue(data["gate_pass"])
        self.assertEqual(data["passed"], data["cases"])
        self.assertEqual(data["phase_seven_status"], "complete")


if __name__ == "__main__":
    unittest.main()
