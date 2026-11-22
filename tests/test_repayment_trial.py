from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from scripts import run_repayment_trial as trial
from scripts.run_repayment_comparison import summarize


class RepaymentTrialTests(unittest.TestCase):
    def test_three_way_gate_excludes_rounds_with_blocked_grading(self):
        variants = ['baseline', 'superpowers', 'candidate']
        results = [dict(trial=i, variant=v, outcome='pass', holdout='pass')
                   for i in range(1, 4) for v in variants]
        results[4]['holdout'] = 'blocked'
        value = summarize(results, variants)
        self.assertEqual(value['status'], 'insufficient_evidence')
        self.assertEqual(value['matched_trials'], 2)
        results[4]['holdout'] = 'pass'
        results[5]['holdout'] = 'fail'
        self.assertEqual(summarize(results, variants)['status'], 'below_upstream')

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
