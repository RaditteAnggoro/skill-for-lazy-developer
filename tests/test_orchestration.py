from pathlib import Path
import unittest

import yaml

from scripts.simulate_phase_orchestration import simulate
from scripts.validate_phase_plan import known_skills, validate_case, validate_plan


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tests/orchestration_cases.yaml"


class PhaseOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.cases = yaml.safe_load(CASES.read_text(encoding="utf-8"))["cases"]
        self.skills = known_skills()

    def test_all_phase_plans_are_valid(self):
        for case in self.cases:
            self.assertEqual(validate_case(case, self.skills), [], case["id"])

    def test_mixed_backend_ui_case_has_a_complete_sequence(self):
        case = next(item for item in self.cases if item["id"] == "invoice-backend-and-ui")
        primaries = [phase["primary"] for phase in case["plan"]["phases"]]
        for skill in (
            "research-plan-implement",
            "lean-senior-engineering",
            "ui-implementation",
            "browser-journey-testing",
            "ui-quality-verification",
            "spec-to-code-verification",
            "verification-before-completion",
        ):
            self.assertIn(skill, primaries)
        self.assertEqual(primaries[-1], "verification-before-completion")
        self.assertNotIn("adaptive-workflow", primaries)

    def test_backend_only_case_does_not_add_ui_work(self):
        case = next(item for item in self.cases if item["id"] == "backend-contract-only")
        primaries = [phase["primary"] for phase in case["plan"]["phases"]]
        self.assertNotIn("ui-implementation", primaries)
        support = [name for phase in case["plan"]["phases"] for name in phase.get("support", [])]
        self.assertIn("transaction-safe-engineering", support)

    def test_design_phase_precedes_ui_implementation(self):
        case = next(item for item in self.cases if item["id"] == "unresolved-ui-direction")
        primaries = [phase["primary"] for phase in case["plan"]["phases"]]
        self.assertLess(primaries.index("ui-design-intelligence"), primaries.index("ui-implementation"))

    def test_ui_journey_and_audit_are_separate_dependent_phases(self):
        for case in self.cases:
            phases = case["plan"]["phases"]
            implementation = next((p for p in phases if p["primary"] == "ui-implementation"), None)
            if implementation is None:
                continue
            journey = next(p for p in phases if p["primary"] == "browser-journey-testing")
            audit = next(p for p in phases if p["primary"] == "ui-quality-verification")
            self.assertIn(implementation["id"], journey["depends_on"], case["id"])
            self.assertIn(journey["id"], audit["depends_on"], case["id"])

    def test_invalid_plans_are_rejected(self):
        base = {
            "phases": [
                {"id": "one", "primary": "lean-senior-engineering", "entry": "x", "exit": "y", "evidence": "z"},
                {"id": "two", "primary": "verification-before-completion", "support": [], "depends_on": ["one"], "entry": "x", "exit": "y", "evidence": "z"},
            ]
        }
        self.assertEqual(validate_plan(base, self.skills), [])
        no_dependency = {
            "phases": [
                {"id": "one", "primary": "lean-senior-engineering", "entry": "x", "exit": "y", "evidence": "z"},
                {"id": "two", "primary": "verification-before-completion", "support": [], "entry": "x", "exit": "y", "evidence": "z"},
            ]
        }
        self.assertTrue(any("must declare depends_on" in error for error in validate_plan(no_dependency, self.skills)))
        router_support = {
            "phases": [
                {"id": "one", "primary": "lean-senior-engineering", "support": ["adaptive-workflow"], "entry": "x", "exit": "y", "evidence": "z"},
                {"id": "two", "primary": "verification-before-completion", "support": [], "depends_on": ["one"], "entry": "x", "exit": "y", "evidence": "z"},
            ]
        }
        self.assertTrue(any("router as a support" in error for error in validate_plan(router_support, self.skills)))
        back_dependency = {
            "phases": [
                {"id": "one", "primary": "lean-senior-engineering", "entry": "x", "exit": "y", "evidence": "z"},
                {"id": "two", "primary": "ui-implementation", "depends_on": ["final"], "entry": "x", "exit": "y", "evidence": "z"},
                {"id": "final", "primary": "verification-before-completion", "depends_on": ["one"], "entry": "x", "exit": "y", "evidence": "z"},
            ]
        }
        self.assertTrue(any("must depend on an earlier phase" in error for error in validate_plan(back_dependency, self.skills)))
        final_not_all = {
            "phases": [
                {"id": "one", "primary": "lean-senior-engineering", "entry": "x", "exit": "y", "evidence": "z"},
                {"id": "two", "primary": "ui-implementation", "depends_on": ["one"], "entry": "x", "exit": "y", "evidence": "z"},
                {"id": "final", "primary": "verification-before-completion", "depends_on": ["one"], "entry": "x", "exit": "y", "evidence": "z"},
            ]
        }
        self.assertTrue(any("all work phases" in error for error in validate_plan(final_not_all, self.skills)))

    def test_malformed_phases_return_errors_instead_of_crashing(self):
        self.assertTrue(validate_plan({"phases": [None]}, self.skills))
        self.assertTrue(validate_plan({"phases": [{"id": "one", "primary": "lean-senior-engineering", "depends_on": 123, "entry": "x", "exit": "y", "evidence": "z"}]}, self.skills))
        self.assertTrue(validate_plan({"phases": [{"id": [], "primary": "lean-senior-engineering", "entry": "x", "exit": "y", "evidence": "z"}]}, self.skills))
        self.assertTrue(validate_plan({"phases": [{"id": "one", "primary": "lean-senior-engineering", "depends_on": [], "entry": "x", "exit": "y", "evidence": "z"}, {"id": [], "primary": "verification-before-completion", "depends_on": ["one"], "entry": "x", "exit": "y", "evidence": "z"}]}, self.skills))
        self.assertTrue(validate_plan({"phases": [{"id": [], "primary": "lean-senior-engineering", "entry": "x", "exit": "y", "evidence": "z"}, {"id": "final", "primary": "verification-before-completion", "depends_on": ["missing"], "entry": "x", "exit": "y", "evidence": "z"}]}, self.skills))

    def test_browser_failure_uses_the_documented_route(self):
        case = next(item for item in self.cases if item["id"] == "browser-failure-and-ui-fix")
        first = case["plan"]["phases"][0]
        self.assertEqual(first["primary"], "browser-diagnostics")
        self.assertEqual(first["support"], ["systematic-debugging"])
        self.assertEqual(case["expected_phases"][0], "browser-diagnostics")

    def test_mock_executor_emits_trace_and_does_not_ask_between_phases(self):
        case = next(item for item in self.cases if item["id"] == "invoice-backend-and-ui")
        result = simulate(case["plan"], self.skills)
        self.assertEqual(
            [item["skill"] for item in result["trace"]],
            [
                "research-plan-implement",
                "lean-senior-engineering",
                "ui-implementation",
                "browser-journey-testing",
                "ui-quality-verification",
                "spec-to-code-verification",
                "verification-before-completion",
            ],
        )
        self.assertFalse(result["asked_user_between_phases"])
        self.assertEqual(result["trace"][-1]["skill"], "verification-before-completion")
        for item in result["trace"]:
            self.assertTrue(item["evidence"])
        self.assertIn("verification-before-completion", result["final_report"])

    def test_adaptive_skill_has_phase_re_routing_and_trace(self):
        text = " ".join((ROOT / ".agents/skills/adaptive-workflow/SKILL.md").read_text(encoding="utf-8").lower().split())
        for phrase in ("phase orchestration", "skill trace", "phase trace", "do not ask", "per-phase limit"):
            self.assertIn(phrase, text)
        self.assertIn("research-plan-implement", text)

    def test_research_skill_has_phase_plan_contract(self):
        text = " ".join((ROOT / ".agents/skills/research-plan-implement/SKILL.md").read_text(encoding="utf-8").lower().split())
        for phrase in ("phase plan", "one primary skill", "skill trace", "authorized_scope", "final verification"):
            self.assertIn(phrase, text)

    def test_evidence_records_seamless_orchestration(self):
        data = yaml.safe_load((ROOT / "tests/phase_orchestration_evidence.yaml").read_text(encoding="utf-8"))
        self.assertTrue(data["gate_pass"])
        self.assertEqual(data["cases"], len(self.cases))
        self.assertEqual(data["passed"], data["cases"])
        self.assertTrue(data["mock_trace_verified"])
        self.assertEqual(data["live_agent_execution"], "not_tested")
        self.assertEqual(data["runtime_enforcement"], "absent")
        self.assertIn("single-agent", " ".join(data["limitations"]).lower())


if __name__ == "__main__":
    unittest.main()
