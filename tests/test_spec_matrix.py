from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "tests/hermes_spec_matrix.yaml"
ALLOWED = {"STATIC", "SIMULATED", "REPOSITORY_INTEGRATION", "NOT_RUN", "BLOCKED", "DEFERRED"}


class SpecMatrixTests(unittest.TestCase):
    def test_48_spec_cases_are_explicitly_accounted_for(self):
        data = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
        cases = data["cases"]
        self.assertEqual(len(cases), 48)
        self.assertEqual({case["id"] for case in cases}, {"LD-{:03d}".format(i) for i in range(1, 49)})
        for case in cases:
            self.assertIn(case["level"], ALLOWED)
            self.assertTrue(case["scenario"] and case["evidence"] and case["note"])
            self.assertTrue((ROOT / case["evidence"]).exists(), case["id"])

    def test_not_run_is_not_reported_as_pass(self):
        data = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
        not_run = [case for case in data["cases"] if case["level"] in {"NOT_RUN", "BLOCKED", "DEFERRED"}]
        self.assertGreaterEqual(len(not_run), 1)
        for case in not_run:
            self.assertFalse(case["note"].lower().startswith("pass"), case["id"])


if __name__ == "__main__":
    unittest.main()
