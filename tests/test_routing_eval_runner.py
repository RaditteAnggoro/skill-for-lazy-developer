from pathlib import Path
import tempfile
import unittest

from scripts.run_routing_evals import (
    build_command,
    load_cases,
    score_case,
    score_message,
    select_cases,
)


class RoutingEvalRunnerTests(unittest.TestCase):
    def test_loads_and_selects_cases_in_requested_order(self):
        cases = load_cases()
        selected = select_cases(cases, ["review-only", "failing-unit-test"])
        self.assertEqual(
            [case["id"] for case in selected],
            ["review-only", "failing-unit-test"],
        )

    def test_rejects_unknown_case(self):
        with self.assertRaisesRegex(ValueError, "unknown case id"):
            select_cases(load_cases(), ["not-a-real-case"])

    def test_prepared_workspace_omits_local_artifacts(self):
        from scripts.run_routing_evals import prepare_workspace
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            prepare_workspace(workspace)
            self.assertTrue((workspace / ".agents/skills/adaptive-workflow/SKILL.md").is_file())
            self.assertFalse((workspace / ".agents/artifacts").exists())

    def test_builds_read_only_ephemeral_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            command = build_command("codex-test", root, root / "result.json", "model-x")
        self.assertEqual(command[0:2], ["codex-test", "exec"])
        self.assertIn("--ephemeral", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("read-only", command)
        self.assertIn("--output-schema", command)
        self.assertEqual(command[-2:], ["--model", "model-x"])

    def test_scores_only_routing_contract_fields(self):
        case = {
            "interaction": "automatic",
            "primary": "systematic-debugging",
            "supporting": ["verification-before-completion"],
        }
        actual = dict(case, user_message="I will investigate and verify the failure.")
        self.assertEqual(score_case(case, actual), [])
        actual["primary"] = "lean-senior-engineering"
        self.assertEqual(len(score_case(case, actual)), 1)

    def test_allows_only_declared_interactive_alternatives(self):
        case = {
            "interaction": "choice",
            "accepted_interactions": ["choice", "question"],
            "primary": "feature-discovery",
            "supporting": [],
        }
        actual = {
            "interaction": "question",
            "primary": "feature-discovery",
            "supporting": [],
            "user_message": "Which outcome matters most for this feature?",
        }
        self.assertEqual(score_case(case, actual), [])
        actual["interaction"] = "automatic"
        self.assertEqual(len(score_case(case, actual)), 1)

    def test_message_grader_rejects_boilerplate_and_redundant_question(self):
        case = {
            "message_expectations": {
                "language": "en",
                "question": "forbidden",
                "max_words": 30,
            }
        }
        differences = score_message(
            case, "Great idea. Would you like me to investigate the failure?"
        )
        self.assertEqual(len(differences), 3)

    def test_message_grader_rejects_formal_customer_service_language(self):
        self.assertEqual(
            score_message({}, "Your request has been received. I will now proceed."),
            [
                "user_message contains boilerplate "
                "'your request has been received'"
            ],
        )

    def test_message_grader_accepts_concise_indonesian_continuation(self):
        case = {
            "message_expectations": {
                "language": "id",
                "question": "forbidden",
                "max_words": 30,
            }
        }
        self.assertEqual(
            score_message(
                case,
                "Saya akan reproduksi kegagalannya, cari penyebab, lalu jalankan pengecekan terkait.",
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
