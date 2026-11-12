from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from scripts import run_repayment_trial as trial


class RepaymentTrialTests(unittest.TestCase):
    def test_synthetic_grader_does_not_pass_when_no_checks_ran(self):
        cases = [
            (SimpleNamespace(returncode=0, stderr=b''), 'blocked'),
            (SimpleNamespace(returncode=0, stderr=b'Ran 3 tests\n\nOK\n'), 'pass'),
            (SimpleNamespace(returncode=1, stderr=b'Ran 3 tests\nFAILED (failures=1)\n'), 'fail'),
            (SimpleNamespace(returncode=1, stderr=b'permission denied'), 'blocked'),
        ]
        for completed, expected in cases:
            with self.subTest(expected=expected), mock.patch.object(trial.subprocess, 'run', return_value=completed):
                self.assertEqual(trial.grade_copy('codex', Path('/tmp/synthetic'))[0], expected)

    def test_failed_preflight_never_runs_model(self):
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(trial, 'preflight', return_value=False), \
             mock.patch.object(trial, 'run_one') as model:
            code = trial.main(['--ref', 'HEAD', '--variant', 'baseline', '--model', 'example',
                               '--output', str(Path(tmp)/'report.json')])
            self.assertEqual(code, 2)
            model.assert_not_called()

    def test_protected_grader_and_agent_files_are_part_of_profile(self):
        self.assertIn('"verify.py"="read"', trial.TASK_FILESYSTEM)
        self.assertIn('"AGENTS.md"="read"', trial.TASK_FILESYSTEM)
        self.assertIn('".agents"="read"', trial.TASK_FILESYSTEM)
        self.assertIn('permissions.eval.network.enabled=false', trial.task_options())
        self.assertIn('hooks', trial.task_options())


if __name__ == '__main__':
    unittest.main()
