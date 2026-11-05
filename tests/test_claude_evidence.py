from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "tests/claude_adapter_evidence.yaml"


class ClaudeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = yaml.safe_load(EVIDENCE.read_text(encoding="utf-8"))

    def test_hook_contract_checks_pass(self):
        checks = self.data["checks"]
        self.assertEqual(sum(1 for value in checks.values() if value), self.data["checks_total"])
        for key, value in checks.items():
            self.assertTrue(value, key)

    def test_live_claude_delivery_is_not_claimed(self):
        self.assertFalse(self.data["host"]["binary_available"])
        self.assertFalse(self.data["host"]["authenticated_session"])
        self.assertFalse(self.data["live_model_delivery"])

    def test_handoff_and_adapter_files_are_explicit(self):
        self.assertEqual(self.data["handoff"]["kind"], "conditional")
        self.assertEqual(self.data["handoff"]["verified_confidence"], 0.9)
        self.assertFalse(self.data["handoff"]["raw_transcript_stored"])
        self.assertTrue(self.data["forget"]["two_step_confirmation"])
        for relative in (
            "scripts/install_claude_adapter.py",
            "tests/test_claude_adapter.py",
            "adapters/claude/README.md",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_claude_is_deferred_while_phase_three_is_complete(self):
        self.assertEqual(self.data["phase_three_status"], "complete")
        self.assertEqual(
            self.data["phase_three_verification"], "verified-with-deferred-claude"
        )
        self.assertFalse(self.data["live_model_delivery"])


if __name__ == "__main__":
    unittest.main()
