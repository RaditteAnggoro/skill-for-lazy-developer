from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class OneShotPolicyTests(unittest.TestCase):
    def test_snippet_has_one_shot_rule_and_budget(self):
        text = " ".join((ROOT / "AGENTS.snippet.md").read_text(encoding="utf-8").lower().split())
        self.assertIn("finish the authorized task in one pass", text)
        self.assertIn("ask only when a missing decision or permission", text)
        self.assertLessEqual(len(text.split()), 640)

    def test_adaptive_skill_has_execution_boundary(self):
        text = " ".join((ROOT / ".agents/skills/adaptive-workflow/SKILL.md").read_text(encoding="utf-8").lower().split())
        self.assertIn("one-shot execution", text)
        self.assertIn("finish the whole task in one pass", text)
        self.assertIn("does not mean ignoring a real blocker", text)

    def test_readme_has_one_shot_info(self):
        text = " ".join((ROOT / "README.md").read_text(encoding="utf-8").lower().split())
        self.assertIn("one-shot coding", text)
        self.assertIn("does not ask for approval between routine steps", text)


if __name__ == "__main__":
    unittest.main()
