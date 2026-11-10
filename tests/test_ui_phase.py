from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents/skills"


class UiPhaseTests(unittest.TestCase):
    def test_journey_workflow_covers_design_and_browser_gaps(self):
        journey = (SKILLS / "browser-journey-testing/SKILL.md").read_text(encoding="utf-8").lower()
        for phrase in ("primary journey", "design", "repeated controls", "keyboard", "no browser", "not a browser test"):
            self.assertIn(phrase, journey)
        implementation = (SKILLS / "ui-implementation/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("browser-journey-testing", implementation)

    def test_ui_skills_exist_with_focused_boundaries(self):
        for name, phrases in (
            ("ui-design-intelligence", ("direction", "enterprise data")),
            ("ui-implementation", ("responsive", "empty", "loading", "error")),
            ("ui-quality-verification", ("screenshot", "keyboard", "responsive")),
        ):
            text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("name: {}".format(name), text)
            for phrase in phrases:
                self.assertIn(phrase.lower(), text.lower(), (name, phrase))

    def test_enterprise_profiles_cover_requested_patterns(self):
        text = (SKILLS / "ui-design-intelligence/references/enterprise-data-ux.md").read_text(
            encoding="utf-8"
        ).lower()
        for phrase in ("dense tables", "filters", "approvals", "long forms", "reconciliation", "financial"):
            self.assertIn(phrase, text)

    def test_browser_diagnostics_has_a_boundary_not_an_audit_copy(self):
        text = (SKILLS / "browser-diagnostics/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Boundary with UI quality verification", text)
        self.assertIn("ui-quality-verification", text)
        self.assertIn("unexplained failure", text)

    def test_fixtures_and_snapshots_exist(self):
        for relative in (
            "tests/ui/fixtures/plain/index.html",
            "tests/ui/fixtures/react/src/main.jsx",
            "tests/ui/fixtures/next/app/page.jsx",
            "tests/ui/fixtures/shared/EnterpriseApprovals.jsx",
            "tests/ui/run_ui_checks.mjs",
            "tests/ui/run_next_checks.mjs",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)
        for fixture in ("plain", "react", "next"):
            for width in (360, 1440):
                self.assertTrue(
                    (ROOT / "tests/ui/snapshots/{}-{}.png".format(fixture, width)).is_file(),
                    (fixture, width),
                )

    def test_ui_evidence_passes_and_states_limitations(self):
        data = yaml.safe_load((ROOT / "tests/ui/evidence.yaml").read_text(encoding="utf-8"))
        self.assertTrue(data["gate_pass"])
        self.assertEqual(data["phase_five_status"], "complete")
        self.assertEqual(data["checks"]["plain_and_react_passed"], 35)
        self.assertEqual(data["checks"]["next_passed"], 12)
        for key in ("empty", "loading", "error"):
            self.assertEqual(data["states"][key], "pass")
        limits = " ".join(data["limitations"]).lower()
        self.assertIn("chrome", limits)
        self.assertIn("assistive", limits)


if __name__ == "__main__":
    unittest.main()
