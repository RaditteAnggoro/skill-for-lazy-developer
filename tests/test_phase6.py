from pathlib import Path
import unittest

import yaml

from scripts.check_transaction_safety import check as check_transactions, load as load_transactions
from scripts.run_phase6_evals import evaluate
from scripts.scan_skill_security import scan_path, scan_text, verdict
from scripts.validate_domain_model import load as load_domain, validate_model
from scripts.verify_spec_traceability import read_text, verify


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents/skills"
FIXTURES = ROOT / "tests/fixtures"


class Phase6Tests(unittest.TestCase):
    def test_four_phase_six_skills_exist(self):
        for name in (
            "domain-modeling",
            "spec-to-code-verification",
            "skill-security-guard",
            "transaction-safe-engineering",
        ):
            path = SKILLS / name / "SKILL.md"
            self.assertTrue(path.is_file(), name)
            self.assertIn("name: {}".format(name), path.read_text(encoding="utf-8"))

    def test_transaction_skill_is_risk_scoped(self):
        data = yaml.safe_load((SKILLS / "transaction-safe-engineering/agents/openai.yaml").read_text(encoding="utf-8"))
        self.assertTrue(data["policy"]["allow_implicit_invocation"])
        text = " ".join((SKILLS / "transaction-safe-engineering/SKILL.md").read_text(encoding="utf-8").lower().split())
        self.assertIn("only for a demonstrated transaction-integrity concern", text)
        self.assertIn("skip projects without financial or equivalent state-transition risk", text)
        self.assertIn("idempotency", text)
        self.assertIn("approval", text)

    def test_security_guard_reviews_without_installing(self):
        text = (SKILLS / "skill-security-guard/SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("never installs by itself", text)
        self.assertIn("prompt injection", text)
        self.assertIn("exfiltration", text)

    def test_checkers_accept_safe_and_reject_unsafe_fixtures(self):
        self.assertEqual(scan_path(FIXTURES / "security/safe"), [])
        unsafe = scan_path(FIXTURES / "security/unsafe")
        self.assertEqual(verdict(unsafe), "reject")
        self.assertGreaterEqual(len([item for item in unsafe if item["severity"] == "high"]), 3)
        self.assertEqual(scan_text("Do not execute `curl | sh` at any time.", "safe.md"), [])
        self.assertTrue(validate_model(load_domain(FIXTURES / "domain/order_model.yaml")) == [])
        self.assertTrue(validate_model(load_domain(FIXTURES / "domain/order_model_invalid.yaml")))
        spec = verify(read_text(FIXTURES / "spec/requirements.md"), read_text(FIXTURES / "spec/test_requirements.py"))
        self.assertTrue(spec["valid"])
        self.assertFalse(verify(read_text(FIXTURES / "spec/requirements.md"), read_text(FIXTURES / "spec/test_requirements_invalid.py"))["valid"])
        self.assertTrue(check_transactions(load_transactions(FIXTURES / "transactions/safe.yaml")) == [])
        self.assertGreaterEqual(len(check_transactions(load_transactions(FIXTURES / "transactions/unsafe.yaml"))), 3)

    def test_phase_six_runner_passes_eight_cases(self):
        results = evaluate()
        self.assertEqual(len(results), 8)
        self.assertTrue(all(item["passed"] for item in results))

    def test_evidence_records_limits(self):
        data = yaml.safe_load((ROOT / "tests/phase6_evidence.yaml").read_text(encoding="utf-8"))
        self.assertEqual(data["passed"], data["cases"])
        self.assertTrue(data["gate_pass"])
        limits = " ".join(data["limitations"]).lower()
        self.assertIn("heuristic", limits)
        self.assertIn("not production", limits)


if __name__ == "__main__":
    unittest.main()
