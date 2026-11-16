from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from scripts.agent_setup_preview import main, preview


ROOT = Path(__file__).resolve().parents[1]


class SetupPreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.target = Path(self.temp.name)
        (self.target / ".agents/skills/adaptive-workflow").mkdir(parents=True)
        (self.target / ".agents/skills/adaptive-workflow/SKILL.md").write_text("# old\n", encoding="utf-8")
        (self.target / "AGENTS.md").write_text("# instructions\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_preview_is_read_only_and_reports_plan(self):
        before = sorted(str(path) for path in self.target.rglob("*"))
        report = preview(self.target, with_roles=True, with_memory=False, with_ui=False)
        self.assertEqual(report["mode"], "preview-only")
        self.assertIn("skills (17)", report["would_import"])
        self.assertIn("roles (4)", report["would_import"])
        self.assertIn("adaptive-workflow", report["conflicts"])
        self.assertIn("never imported", report["secrets"])
        self.assertEqual(before, sorted(str(path) for path in self.target.rglob("*")))

    def test_cli_json_and_human_output(self):
        self.assertEqual(main(["--target", str(self.target), "--json"]), 0)
        self.assertEqual(main(["--target", str(self.target)]), 0)

    def test_missing_required_memory_fails_strict_mode(self):
        with patch("scripts.agent_setup_preview.which", return_value=None):
            report = preview(self.target, with_roles=False, with_memory=True, with_ui=False)
        self.assertTrue(any(item["name"] == "Engram memory binary" and item["required"] for item in report["requirements"]))
        self.assertIn("Engram memory binary", report["missing_required"])
        with patch("scripts.agent_setup_preview.which", return_value=None):
            self.assertEqual(main(["--target", str(self.target), "--with-memory", "--strict"]), 1)

    def test_missing_target_fails_strict_mode(self):
        missing = self.target / "does-not-exist"
        self.assertEqual(main(["--target", str(missing), "--strict"]), 1)

    def test_docs_explain_preview_boundary(self):
        text = (ROOT / "docs/SETUP_PREVIEW.md").read_text(encoding="utf-8").lower()
        self.assertIn("no files are modified", text)
        self.assertIn("secrets", text)
        self.assertIn("not an installer", text)


if __name__ == "__main__":
    unittest.main()
