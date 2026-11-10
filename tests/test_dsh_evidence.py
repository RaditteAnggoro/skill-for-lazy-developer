from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "tests/dsh_adapter_evidence.yaml"


class DshEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = yaml.safe_load(EVIDENCE.read_text(encoding="utf-8"))

    def test_catalog_reports_nine_skills(self):
        self.assertEqual(self.data["skill_catalog"]["observed"], 16)
        self.assertEqual(len(self.data["skill_catalog"]["names"]), 16)
        self.assertLessEqual(
            set(self.data["skill_catalog"]["names"]),
            {
                path.parent.name
                for path in (ROOT / ".agents/skills").glob("*/SKILL.md")
            },
        )

    def test_routing_uses_the_full_corpus_and_passes(self):
        routing = self.data["routing"]
        self.assertEqual(routing["passed"], routing["total"])
        self.assertGreaterEqual(routing["total"], 24)
        self.assertTrue(routing["read_only_snapshot"])
        self.assertTrue(routing["interaction_cases"])

    def test_memory_and_bundle_lifecycle_checks_are_complete(self):
        memory = self.data["memory"]
        self.assertEqual(memory["checks_passed"], memory["checks_total"])
        for key in (
            "bundle_manifest",
            "save_search",
            "context",
            "restart",
            "delete",
            "isolation",
            "privacy_guard",
            "fail_open_config",
        ):
            self.assertTrue(memory[key], key)
        lifecycle = self.data["bundle_lifecycle"]
        self.assertEqual(lifecycle["checks_passed"], lifecycle["checks_total"])
        for key in ("bundle_rows", "fail_open", "rows_removed", "still_works"):
            self.assertTrue(lifecycle[key], key)

    def test_privacy_and_phase_boundaries_are_explicit(self):
        self.assertTrue(self.data["privacy"]["guard_blocks_sensitive_write"])
        self.assertTrue(self.data["privacy"]["provider_canary_removed"])
        self.assertEqual(self.data["phase_three_verification"], "verified-with-deferred-claude")

    def test_lifecycle_is_verified_live(self):
        lifecycle = self.data["lifecycle"]
        for key in (
            "automatic_recall_unit",
            "remember_unit",
            "show_unit",
            "opt_out_unit",
            "handoff_unit",
            "verified_handoff_unit",
            "forget_two_step_unit",
            "live_forget",
            "live_model_delivery",
            "live_uninstall",
            "live_fail_open",
            "live_opt_out",
            "transport_failure_fixed",
        ):
            self.assertTrue(lifecycle[key], key)
        self.assertIn("message identity", lifecycle["root_cause"])

    def test_adapter_installer_checks_are_recorded(self):
        for key, value in self.data["adapter_installer"].items():
            self.assertEqual(value, "pass", key)


if __name__ == "__main__":
    unittest.main()
