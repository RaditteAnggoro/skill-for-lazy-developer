from pathlib import Path
import unittest

import yaml

from scripts.evaluate_phase1_enhancements import decide


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tests/phase1_enhancement_cases.yaml"


class Phase1GateTests(unittest.TestCase):
    def setUp(self):
        self.cases = yaml.safe_load(CASES.read_text(encoding="utf-8"))["cases"]

    def test_effective_vs_excessive_use(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(sorted(decide(case)), sorted(case["expected"]))

    def test_simple_tasks_do_not_apply_ceremony(self):
        for task_kind in ("simple_copy", "explanation", "docs"):
            case = next(item for item in self.cases if item["task_kind"] == task_kind)
            self.assertEqual(decide(case), [], task_kind)

    def test_high_risk_applies_invariant_first_checks(self):
        case = next(item for item in self.cases if item["id"] == "financial-retry")
        self.assertIn("tdd", decide(case))
        self.assertIn("review", decide(case))

    def test_no_new_skill_count(self):
        skills = list((ROOT / ".agents/skills").glob("*/SKILL.md"))
        self.assertEqual(len(skills), 17)

    def test_phase1_references_exist(self):
        for relative in (
            ".agents/skills/lean-senior-engineering/references/review-and-simplify.md",
            ".agents/skills/systematic-debugging/references/api-debugging.md",
            ".agents/skills/research-plan-implement/references/spike-contract.md",
            ".agents/skills/feature-discovery/references/spikes-and-actions.md",
            ".agents/skills/spec-to-code-verification/references/evidence-ledger.md",
            ".agents/skills/browser-journey-testing/references/exploratory-charter.md",
            ".agents/skills/ui-quality-verification/references/exploratory-qa.md",
            ".agents/skills/ui-design-intelligence/references/adversarial-ux.md",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
