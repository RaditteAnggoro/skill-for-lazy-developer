from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tests/hermes_enhancement_cases.yaml"


class HermesEnhancementContractTests(unittest.TestCase):
    def setUp(self):
        self.cases = yaml.safe_load(CASES.read_text(encoding="utf-8"))["cases"]

    def test_cases_reference_existing_skills_and_references(self):
        skills = {path.parent.name for path in (ROOT / ".agents/skills").glob("*/SKILL.md")}
        self.assertGreaterEqual(len(self.cases), 10)
        for case in self.cases:
            self.assertIn(case["primary"], skills, case["id"])
            for support in case["support"]:
                self.assertIn(support, skills, case["id"])
            self.assertTrue((ROOT / case["reference"]).is_file(), case["id"])

    def test_quality_upgrades_are_present(self):
        required = {
            "lean-senior-engineering": ["review-and-simplify.md", "risk-weighted TDD"],
            "systematic-debugging": ["api-debugging.md", "GraphQL"],
            "research-plan-implement": ["spike-contract.md", "cleanup"],
            "feature-discovery": ["spikes-and-actions.md", "source_id"],
            "spec-to-code-verification": ["evidence-ledger.md", "NOT_APPLICABLE"],
            "browser-journey-testing": ["exploratory-charter.md", "BLOCKED"],
            "ui-quality-verification": ["exploratory-qa.md", "counterexample"],
            "ui-design-intelligence": ["adversarial-ux.md", "duplicated"],
        }
        for skill, phrases in required.items():
            text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in (ROOT / ".agents/skills" / skill).rglob("*")
                if path.is_file()
            )
            for phrase in phrases:
                self.assertIn(phrase, text, (skill, phrase))

    def test_negative_cases_do_not_force_tools_or_agents(self):
        no_browser = next(case for case in self.cases if case["id"] == "simple-no-browser")
        self.assertEqual(no_browser["support"], [])
        self.assertEqual(no_browser["primary"], "architecture-map")
        one_line = next(case for case in self.cases if case["id"] == "one-line-copy")
        self.assertEqual(one_line["support"], [])

    def test_evidence_level_is_not_overclaimed(self):
        text = (ROOT / "tests/hermes_enhancement_cases.yaml").read_text(encoding="utf-8").lower()
        self.assertIn("static/simulated", text)
        self.assertIn("no model or browser", text)


if __name__ == "__main__":
    unittest.main()
