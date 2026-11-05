from pathlib import Path
import tempfile
import unittest

import yaml

from scripts.context_optimizer import (
    RawEvidenceStore,
    count_tokens,
    optimize_case,
    run,
    summarize,
)


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tests/token_optimization_cases.yaml"


class ContextOptimizerTests(unittest.TestCase):
    def setUp(self):
        self.cases = yaml.safe_load(CASES.read_text(encoding="utf-8"))["cases"]

    def test_corpus_has_representative_cases_and_constraints(self):
        self.assertGreaterEqual(len(self.cases), 6)
        for case in self.cases:
            self.assertTrue(case["must_include"])
            self.assertTrue(case["constraints"])
            self.assertIn("scope", case["memory"][0])

    def test_benchmark_meets_reduction_correctness_and_recovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            results = run(self.cases, Path(temporary) / "raw")
            summary = summarize(results)
        self.assertGreaterEqual(summary["median_reduction_percent"], 30)
        self.assertGreaterEqual(summary["min_reduction_percent"], 30)
        self.assertTrue(summary["correct_cases"])
        self.assertTrue(summary["constraints_preserved"])
        self.assertTrue(summary["raw_tool_recovered"])
        self.assertTrue(summary["raw_source_recovered"])
        self.assertTrue(summary["gate_pass"])
        for result in results:
            self.assertLessEqual(result["optimized_chars"], 6000)

    def test_optimizer_is_project_scoped_and_drops_distractors(self):
        case = next(item for item in self.cases if item["id"] == "invoice-reconcile")
        with tempfile.TemporaryDirectory() as temporary:
            result = optimize_case(case, RawEvidenceStore(Path(temporary)))
        self.assertIn("invoice-reconcile-rel-2", result["selected_memory"])
        self.assertIn("invoice-reconcile-other-1", result["omitted_memory"])
        self.assertNotIn("Office wifi", result["optimized"])

    def test_expected_facts_do_not_change_optimizer_output(self):
        case = dict(self.cases[0])
        with tempfile.TemporaryDirectory() as temporary:
            store = RawEvidenceStore(Path(temporary))
            before = optimize_case(case, store)["optimized"]
            case["must_include"] = ["a completely different expected answer"]
            after = optimize_case(case, store)["optimized"]
        self.assertEqual(before, after)

    def test_unfamiliar_critical_information_is_preserved(self):
        case = {"id": "loss-probe", "project": "demo", "task": "Diagnose the batch failure",
                "memory": [], "tool_output": "ERROR batch failed\nUse the blue switch before restarting.",
                "source": "", "constraints": [], "must_include": ["blue switch"]}
        with tempfile.TemporaryDirectory() as temporary:
            result = optimize_case(case, RawEvidenceStore(Path(temporary)))
        self.assertIn("Use the blue switch before restarting.", result["optimized"])

    def test_critical_constraints_are_verbatim_not_summarized(self):
        case = next(item for item in self.cases if item["id"] == "refund-approval")
        with tempfile.TemporaryDirectory() as temporary:
            result = optimize_case(case, RawEvidenceStore(Path(temporary)))
        for constraint in case["constraints"]:
            self.assertIn(constraint, result["optimized"])

    def test_raw_evidence_is_recoverable(self):
        case = next(item for item in self.cases if item["id"] == "ledger-batch")
        with tempfile.TemporaryDirectory() as temporary:
            store = RawEvidenceStore(Path(temporary))
            result = optimize_case(case, store)
            self.assertEqual(store.get(result["raw_refs"][0]), case["tool_output"])
            self.assertEqual(store.get(result["raw_refs"][1]), case["source"])
            with self.assertRaises(ValueError):
                store.get("../../etc/passwd")

    def test_tokenizer_is_deterministic(self):
        first, first_name = count_tokens("The ledger is immutable.")
        second, second_name = count_tokens("The ledger is immutable.")
        self.assertEqual((first, first_name), (second, second_name))
        self.assertGreater(first, 0)


if __name__ == "__main__":
    unittest.main()
