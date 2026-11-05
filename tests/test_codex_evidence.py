from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "tests/codex_adapter_evidence.yaml"


class CodexEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = yaml.safe_load(EVIDENCE.read_text(encoding="utf-8"))

    def test_codex_lifecycle_checks_are_complete(self):
        checks = self.data["checks"]
        self.assertEqual(sum(1 for value in checks.values() if value), self.data["checks_total"])
        for key in (
            "recall",
            "remember",
            "handoff",
            "fail_open",
            "opt_out",
            "uninstall",
            "sensitive_write_skipped",
            "installer_idempotent",
            "installer_rollback",
            "unrelated_hooks_preserved",
            "verified_handoff_with_transcript",
            "forget_confirmation",
        ):
            self.assertTrue(checks[key], key)

    def test_codex_hooks_are_explicitly_reviewed(self):
        self.assertTrue(self.data["trust_model"]["hook_review_required"])
        self.assertTrue(self.data["trust_model"]["installation_does_not_trust_hooks"])
        self.assertIn("SessionStart", self.data["hooks_verified"])
        self.assertIn("Stop", self.data["hooks_verified"])

    def test_handoff_is_conditional_on_evidence(self):
        self.assertEqual(self.data["handoff"]["kind"], "conditional")
        self.assertEqual(self.data["handoff"]["verified_confidence"], 0.9)
        self.assertEqual(self.data["handoff"]["unverified_confidence"], 0.6)
        self.assertFalse(self.data["handoff"]["raw_transcript_stored"])
        self.assertTrue(self.data["forget"]["two_step_confirmation"])

    def test_phase_three_is_still_in_progress(self):
        self.assertEqual(self.data["phase_three_verification"], "verified-with-deferred-claude")

    def test_codex_adapter_files_exist(self):
        for relative in (
            "scripts/install_codex_adapter.py",
            "scripts/verify_codex_adapter.py",
            "integrations/codex/memory_runtime.py",
            "tests/test_codex_adapter.py",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
