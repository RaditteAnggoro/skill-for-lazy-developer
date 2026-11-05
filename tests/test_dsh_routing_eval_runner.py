import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.run_dsh_routing_evals import (
    DSH_OVERLAY,
    build_command,
    evaluation_prompt,
    extract_json,
    run_case,
    workspace_snapshot,
)


class DshRoutingEvalRunnerTests(unittest.TestCase):
    def test_builds_profile_command_that_reads_stdin(self):
        command = build_command(Path("/tmp/dsh"), "dsh-eval")
        self.assertEqual(command, ["/tmp/dsh", "--profile", "dsh-eval", "-"])

    def test_extracts_fenced_and_plain_routing_json(self):
        expected = {
            "interaction": "automatic",
            "primary": "systematic-debugging",
            "supporting": ["verification-before-completion"],
            "user_message": "I’ll investigate the failure.",
        }
        self.assertEqual(
            extract_json("```json\n" + json.dumps(expected) + "\n```"), expected
        )
        self.assertEqual(
            extract_json("Here is the route:\n" + json.dumps(expected) + "\nextra"),
            expected,
        )

    def test_rejects_a_response_without_routing_json(self):
        with self.assertRaisesRegex(ValueError, "no routing JSON"):
            extract_json("I will investigate the failure.")

    def test_prompt_preserves_scope_and_requires_json(self):
        prompt = evaluation_prompt(
            {
                "prompt": "Explain the flow, do not edit.",
            }
        )
        self.assertIn("do not edit", prompt)
        self.assertIn("Return only one", " ".join(prompt.split()))
        self.assertIn("JSON object with keys", " ".join(prompt.split()))

    def test_dsh_overlay_records_host_specific_calibration(self):
        text = DSH_OVERLAY.read_text(encoding="utf-8")
        for phrase in (
            "user_message",
            "adaptive-workflow",
            "browser-diagnostics",
            "verification-before-completion",
            "planning request",
        ):
            self.assertIn(phrase, text)

    def test_workspace_snapshot_detects_a_file_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "file.txt").write_text("before", encoding="utf-8")
            before = workspace_snapshot(root)
            (root / "file.txt").write_text("after", encoding="utf-8")
            self.assertNotEqual(before, workspace_snapshot(root))

    def test_run_case_returns_scoring_differences_from_stdout_json(self):
        case = {
            "id": "clear-label-change",
            "prompt": "Change the label.",
            "interaction": "automatic",
            "primary": "lean-senior-engineering",
            "supporting": ["verification-before-completion"],
        }
        payload = {
            "interaction": "automatic",
            "primary": "lean-senior-engineering",
            "supporting": ["verification-before-completion"],
            "user_message": "I’ll change the label and verify it.",
        }
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(payload), stderr=""
        )
        with tempfile.TemporaryDirectory() as temporary:
            with patch(
                "scripts.run_dsh_routing_evals.subprocess.run",
                return_value=completed,
            ):
                result = run_case(
                    case,
                    Path("/tmp/dsh"),
                    "dsh-eval",
                    30,
                    artifacts=Path(temporary) / "artifacts",
                )
            self.assertEqual(result, [])
            self.assertTrue(
                (Path(temporary) / "artifacts/clear-label-change.stdout.txt").is_file()
            )

    def test_run_case_reports_nonzero_exit(self):
        case = {
            "id": "x",
            "prompt": "x",
            "interaction": "automatic",
            "primary": "lean-senior-engineering",
            "supporting": [],
        }
        completed = subprocess.CompletedProcess(
            args=[], returncode=7, stdout="", stderr="failed"
        )
        with patch("scripts.run_dsh_routing_evals.subprocess.run", return_value=completed):
            self.assertEqual(
                run_case(case, Path("/tmp/dsh"), "dsh-eval", 30),
                ["dsh exited with 7"],
            )


if __name__ == "__main__":
    unittest.main()
