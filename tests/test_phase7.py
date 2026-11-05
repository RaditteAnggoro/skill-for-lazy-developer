from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
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
