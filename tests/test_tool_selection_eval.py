import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from scripts import run_tool_selection_eval as evaluation


class ToolSelectionEvalTests(unittest.TestCase):
    def test_expected_answer_is_not_given_to_model(self):
        case = {'id': 'private-id', 'need': 'code', 'expected': 'serena',
                'provider': 'serena', 'state': 'working'}
        text = evaluation.prompt(case)
        self.assertNotIn('"expected"', text)
        self.assertNotIn('private-id', text)
        self.assertIn('"provider": "serena"', text)

    def test_failed_preflight_never_runs_model(self):
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(evaluation, 'isolation_preflight', return_value=False), \
             mock.patch.object(evaluation, 'run_case') as run:
            result = evaluation.main(['--ref', 'HEAD', '--model', 'example', '--output', str(Path(tmp)/'out')])
            self.assertEqual(result, 2)
            run.assert_not_called()

    def test_simulated_selection_scores_without_invoking_mcp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'.agents/skills/example').mkdir(parents=True)
            (root/'.agents/skills/example/SKILL.md').write_text('skill')
            (root/'AGENTS.md').write_text('rules')
            case = {'id':'one', 'need':'code', 'provider':'serena', 'expected':'serena'}
            def fake(command, **kwargs):
                path = Path(command[command.index('--output-last-message') + 1])
                path.write_text(json.dumps({'selected': 'serena'}))
                self.assertIn('web_search="disabled"', command)
                self.assertIn('hooks', command)
                return SimpleNamespace(returncode=0, stderr='')
            with mock.patch.object(evaluation.subprocess, 'run', side_effect=fake):
                result = evaluation.run_case(root, case, 'codex', 'example', 'high', 5)
            self.assertEqual(result, {'outcome':'pass', 'selected':'serena'})


if __name__ == '__main__': unittest.main()
