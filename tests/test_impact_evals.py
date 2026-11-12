import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import yaml
from scripts import run_impact_evals as impact


class ImpactEvalTests(unittest.TestCase):
    def test_recall_precision_penalize_omissions_and_extras(self):
        result = impact.score(['a.py', 'extra.py'], ['a.py', 'b.py'])
        self.assertEqual(result['recall'], 0.5)
        self.assertEqual(result['precision'], 0.5)
        self.assertEqual(result['missing'], ['b.py'])
        self.assertEqual(result['extra'], ['extra.py'])
        self.assertEqual(impact.score([], ['a.py'])['precision'], 0)
        with self.assertRaises(ValueError): impact.score(['a.py'], [])

    def test_cases_have_unique_ids_and_existing_ground_truth(self):
        cases = yaml.safe_load(impact.CASES.read_text())['cases']
        self.assertGreaterEqual(len(cases), 8)
        self.assertEqual(len({x['id'] for x in cases}), len(cases))
        for case in cases:
            self.assertTrue(case['prompt'])
            self.assertEqual(len(case['files']), len(set(case['files'])))
            for name in case['files']:
                self.assertTrue((impact.FIXTURE/name).is_file(), (case['id'], name))

    def test_agent_receives_source_but_not_ground_truth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'.agents/skills/example').mkdir(parents=True)
            (root/'.agents/skills/example/SKILL.md').write_text('skill')
            (root/'AGENTS.md').write_text('rules')
            case={'id':'sample', 'prompt':'Trace the report flow.', 'files':['report.py','ledger.py']}
            def fake(command, **kwargs):
                workspace=Path(command[command.index('--cd')+1])
                self.assertTrue((workspace/'project/report.py').exists())
                self.assertFalse((workspace/'project/impact_cases.yaml').exists())
                self.assertNotIn('ledger.py', kwargs['input'])
                result=Path(command[command.index('--output-last-message')+1])
                result.write_text(json.dumps({'files':['report.py','ledger.py']}))
                return SimpleNamespace(returncode=0,stderr='')
            with mock.patch.object(impact.subprocess,'run',side_effect=fake):
                result=impact.run_case(root,case,'codex','model','high',5)
            self.assertEqual(result['outcome'],'pass')
            self.assertEqual(result['recall'],1)
            self.assertEqual(result['precision'],1)

    def test_schema_avoids_unsupported_unique_items_and_duplicates_are_rejected(self):
        self.assertNotIn('uniqueItems', impact.SCHEMA['properties']['files'])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'.agents/skills/example').mkdir(parents=True)
            (root/'.agents/skills/example/SKILL.md').write_text('skill')
            (root/'AGENTS.md').write_text('rules')
            case={'id':'sample', 'prompt':'Trace.', 'files':['report.py']}
            def fake(command, **kwargs):
                result=Path(command[command.index('--output-last-message')+1])
                result.write_text(json.dumps({'files':['report.py','report.py']}))
                return SimpleNamespace(returncode=0,stderr='')
            with mock.patch.object(impact.subprocess,'run',side_effect=fake):
                result=impact.run_case(root,case,'codex','model','high',5)
            self.assertEqual(result['outcome'],'blocked')

    def test_failed_preflight_does_not_call_model(self):
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(impact,'isolation_preflight',return_value=False), \
             mock.patch.object(impact,'run_case') as model:
            code=impact.main(['--ref','HEAD','--model','example','--output',str(Path(tmp)/'out')])
            self.assertEqual(code,2)
            model.assert_not_called()


if __name__=='__main__': unittest.main()
