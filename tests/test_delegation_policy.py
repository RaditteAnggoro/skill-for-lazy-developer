from pathlib import Path
import unittest

import yaml

from scripts.evaluate_delegation import decide, trace


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tests/delegation_cases.yaml"


class DelegationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.cases = yaml.safe_load(CASES.read_text(encoding="utf-8"))["cases"]

    def test_decision_table(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                decision, role = decide(case)
                self.assertEqual(decision, case["expected"])
                self.assertEqual(role, case.get("role"))

    def test_simple_tasks_do_not_delegate(self):
        simple = [case for case in self.cases if case["expected"] == "single"]
        self.assertGreaterEqual(len(simple), 3)
        for case in simple:
            self.assertFalse(case["independent"] or case["consequence"] == "high")

    def test_unsupported_or_unrestricted_host_falls_back(self):
        fallback = [case for case in self.cases if case["expected"] == "fallback"]
        self.assertGreaterEqual(len(fallback), 2)
        for case in fallback:
            self.assertTrue(not case["host_supported"] or not case["permissions_readonly"])

    def test_trace_distinguishes_simulation_from_live_dispatch(self):
        records = [trace(case) for case in self.cases]
        self.assertTrue(all(item["live_dispatch"] is False for item in records))
        self.assertTrue(all(item["evidence_level"] == "SIMULATED" for item in records))
        delegated = next(item for item in records if item["decision"] == "delegate")
        self.assertEqual(delegated["execution_mode"], "simulated-delegation")
        fallback = next(item for item in records if item["decision"] == "fallback")
        self.assertEqual(fallback["execution_mode"], "single-agent-role-guided")
        self.assertIn(fallback["fallback_reason"], {"host_no_delegation", "permission_restricted"})

    def test_router_policy_mentions_gate_and_fallback(self):
        text = " ".join((ROOT / ".agents/skills/adaptive-workflow/references/delegation-policy.md").read_text(encoding="utf-8").lower().split())
        for phrase in ("one agent", "at most 2", "single-agent fallback", "execution_mode=single-agent-role-guided", "permission_restricted"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
