import os
import unittest
from unittest.mock import patch

from scripts.memory_contract import validate_record
from scripts.run_memory_bakeoff import (
    _probe_record,
    build_records,
    expanded_query,
    load_cases,
    provider_environment,
    recommend,
)


class MemoryBakeoffCaseTests(unittest.TestCase):
    def setUp(self):
        self.cases = load_cases()
        self.records = build_records(self.cases)

    def test_corpus_contains_projects_lifecycle_and_privacy_cases(self):
        ids = {record["id"] for record in self.records}
        self.assertIn("dec-billing-db", ids)
        self.assertIn("dec-billing-db-mysql", ids)
        self.assertIn("stale-invoice-cache", ids)
        self.assertIn("rejected-injection", ids)
        self.assertIn("fact-beta-codename", ids)
        self.assertGreaterEqual(len(self.cases["queries"]), 10)

    def test_every_query_references_a_record_or_an_explicit_empty_result(self):
        ids = {record["id"] for record in self.records}
        projects = {record["scope"]["project"] for record in self.records}
        for query in self.cases["queries"]:
            self.assertIn(query["project"], projects)
            self.assertTrue(set(query["expect"]) <= ids, query["id"])
            self.assertTrue(set(query["forbid"]) <= ids, query["id"])
            by_id = {record["id"]: record for record in self.records}
            for record_id in query["expect"]:
                self.assertEqual(
                    by_id[record_id]["scope"]["project"], query["project"]
                )

    def test_privacy_probe_is_rejected_by_the_contract(self):
        probe = _probe_record(self.cases, self.cases["workspace"])
        errors = validate_record(probe)
        self.assertTrue(errors)
        self.assertIn("sensitive data", " ".join(errors))
        self.assertNotIn("sk-test-", " ".join(errors))

    def test_natural_queries_expand_to_or_but_tokens_stay_exact(self):
        self.assertEqual(
            expanded_query("BILLING-DB-POSTGRES"), "BILLING-DB-POSTGRES"
        )
        expanded = expanded_query("which database does billing use")
        self.assertIn("database OR billing", expanded)
        self.assertNotIn("which", expanded)

    def test_provider_environment_strips_parent_provider_variables(self):
        with patch.dict(
            os.environ,
            {"AI_MEMORY_DATA_DIR": "/parent", "ENGRAM_DATA_DIR": "/parent"},
            clear=False,
        ):
            env = provider_environment(__import__("pathlib").Path("/tmp/root"))
        self.assertNotIn("AI_MEMORY_DATA_DIR", env)
        self.assertNotIn("ENGRAM_DATA_DIR", env)
        self.assertEqual(env["HOME"], "/tmp/root/home")

    def test_recommendation_blocks_when_no_provider_passes(self):
        recommendation = recommend(
            [{"provider": "engram", "passed": False}, {"provider": "ai-memory", "passed": False}]
        )
        self.assertIn("keep Phase 3 blocked", recommendation)

    def test_recommendation_prefers_portable_import_among_passing_providers(self):
        passing = [
            {
                "provider": "engram",
                "passed": True,
                "export": {"import_supported": True},
                "timings": {"setup_ms": 300, "query_ms_median": 10},
            },
            {
                "provider": "ai-memory",
                "passed": True,
                "export": {"import_supported": False},
                "timings": {"setup_ms": 100, "query_ms_median": 5},
            },
        ]
        self.assertIn("engram", recommend(passing))


if __name__ == "__main__":
    unittest.main()
