from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "tests/token_optimization_evidence.yaml"


class TokenEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = yaml.safe_load(EVIDENCE.read_text(encoding="utf-8"))

    def test_phase_four_gate_evidence_passes(self):
        self.assertTrue(self.data["gate_pass"])
        self.assertGreaterEqual(self.data["median_reduction_percent"], 30)
        self.assertGreaterEqual(self.data["min_reduction_percent"], 30)
        self.assertTrue(self.data["correct_cases"])
        self.assertTrue(self.data["constraints_preserved"])
        self.assertTrue(self.data["raw_tool_recovered"])
        self.assertTrue(self.data["raw_source_recovered"])

    def test_phase_four_is_complete(self):
        self.assertEqual(self.data["phase_four_status"], "complete")

    def test_limitations_are_explicit(self):
        limits = " ".join(self.data["limitations"]).lower()
        self.assertIn("not a live model", limits)
        self.assertIn("synthetic", limits)

    def test_optimizer_files_exist(self):
        for relative in (
            "scripts/context_optimizer.py",
            "scripts/run_token_optimization_benchmark.py",
            "tests/token_optimization_cases.yaml",
            "tests/test_context_optimizer.py",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
