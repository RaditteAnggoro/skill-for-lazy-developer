from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.dsh_adapter import (
    AdapterError,
    check_project,
    install,
    rollback,
    uninstall,
)


ROOT = Path(__file__).resolve().parents[1]


class DshAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(ROOT / ".agents", self.root / ".agents")
        (self.root / "AGENTS.md").write_text(
            "# Project rules\n\nKeep this line.\n", encoding="utf-8"
        )

    def test_detects_nine_skills_and_installs_current_block(self):
        before = check_project(self.root)
        self.assertFalse(before["ok"])
        self.assertEqual(before["skill_count"], len(list((ROOT / ".agents/skills").glob("*/SKILL.md"))))
        self.assertEqual(before["block"], "missing")

        result = install(self.root)
        self.assertTrue(result["changed"])
        self.assertTrue(result["backup"])
        after = check_project(self.root)
        self.assertTrue(after["ok"])
        self.assertEqual(after["block"], "current")
        text = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Keep this line.", text)
        self.assertIn("DSH routing calibration", text)

    def test_install_creates_agents_when_absent(self):
        (self.root / "AGENTS.md").unlink()
        result = install(self.root)
        self.assertTrue(result["changed"])
        self.assertIsNone(result["backup"])
        self.assertTrue(check_project(self.root)["ok"])

    def test_install_is_idempotent(self):
        install(self.root)
        first = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        result = install(self.root)
        self.assertFalse(result["changed"])
        self.assertEqual(
            first, (self.root / "AGENTS.md").read_text(encoding="utf-8")
        )

    def test_install_updates_an_outdated_block(self):
        install(self.root)
        instructions = self.root / "AGENTS.md"
        text = instructions.read_text(encoding="utf-8").replace(
            "DSH routing calibration", "Old DSH calibration"
        )
        instructions.write_text(text, encoding="utf-8")
        self.assertFalse(check_project(self.root)["ok"])
        result = install(self.root)
        self.assertTrue(result["changed"])
        self.assertTrue(check_project(self.root)["ok"])

    def test_uninstall_removes_only_the_adapter_block(self):
        install(self.root)
        result = uninstall(self.root)
        self.assertTrue(result["changed"])
        text = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Keep this line.", text)
        self.assertNotIn("DSH routing calibration", text)
        self.assertFalse(check_project(self.root)["ok"])

    def test_rollback_restores_the_pre_install_file(self):
        original = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        result = install(self.root)
        rollback(self.root, result["backup"])
        self.assertEqual(
            original, (self.root / "AGENTS.md").read_text(encoding="utf-8")
        )

    def test_dry_run_does_not_modify_agents(self):
        result = install(self.root, dry_run=True)
        self.assertTrue(result["changed"])
        self.assertNotIn(
            "DSH routing calibration",
            (self.root / "AGENTS.md").read_text(encoding="utf-8"),
        )

    def test_rejects_missing_expected_skill(self):
        shutil.rmtree(self.root / ".agents/skills/systematic-debugging")
        with self.assertRaisesRegex(AdapterError, "missing skills"):
            install(self.root)


if __name__ == "__main__":
    unittest.main()
