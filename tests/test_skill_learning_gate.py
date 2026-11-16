from pathlib import Path
import tempfile
import unittest

import yaml

from scripts.propose_skill_learning import content_error, duplicate, stage, validate


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tests/learning_proposal_cases.yaml"


class SkillLearningGateTests(unittest.TestCase):
    def setUp(self):
        self.cases = yaml.safe_load(CASES.read_text(encoding="utf-8"))["cases"]

    def test_valid_and_rejected_cases(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                data = case["proposal"]
                errors = validate(data)
                problem = content_error(data) if not errors else None
                duplicate_path = duplicate(data) if not errors and not problem else None
                accepted = not errors and not problem and not duplicate_path
                self.assertEqual(accepted, case["expected"] == "accept", errors + [problem or "", duplicate_path or ""])

    def test_staging_never_touches_active_skills(self):
        data = self.cases[0]["proposal"]
        before = (ROOT / ".agents/skills/ui-implementation/SKILL.md").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            path = stage(data, Path(tmp))
            self.assertTrue(path.is_file())
            self.assertEqual(path.parent, Path(tmp))
        self.assertEqual(before, (ROOT / ".agents/skills/ui-implementation/SKILL.md").read_bytes())

    def test_unknown_fields_and_unobserved_evidence_rejected(self):
        data = dict(self.cases[0]["proposal"])
        data["unexpected"] = "value"
        self.assertTrue(validate(data))
        data = dict(self.cases[1]["proposal"])
        self.assertTrue(validate(data))

    def test_policy_and_schema_exist(self):
        self.assertTrue((ROOT / ".agents/skills/adaptive-workflow/references/learning-proposal-policy.md").is_file())
        self.assertTrue((ROOT / "docs/schemas/skill_learning_proposal.schema.json").is_file())


if __name__ == "__main__":
    unittest.main()
