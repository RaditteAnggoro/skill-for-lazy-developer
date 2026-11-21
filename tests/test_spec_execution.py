import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from scripts.verify_spec_traceability import junit_outcomes, verify_execution


class SpecExecutionTests(unittest.TestCase):
    def test_completed_failed_skipped_and_absent_assertions(self):
        with TemporaryDirectory() as temp:
            report = Path(temp) / 'junit.xml'
            report.write_text('''<testsuites><testsuite>
              <testcase classname="journey" name="exact_selection"/>
              <testcase classname="journey" name="no_duplicate"><failure/></testcase>
              <testcase classname="journey" name="retry"><skipped/></testcase>
              <testcase classname="journey" name="dismiss" status="notrun"/>
            </testsuite></testsuites>''', encoding='utf-8')
            spec = '\n'.join(f'REQ-{n} Requirement' for n in range(101, 106))
            mapping = {f'REQ-{n}': [f'journey::{name}'] for n, name in enumerate(
                ('exact_selection', 'no_duplicate', 'retry', 'keyboard', 'dismiss'), 101)}
            result = verify_execution(spec, mapping, junit_outcomes(report))
            self.assertFalse(result['valid'])
            self.assertEqual([item['status'] for item in result['results']],
                             ['passed', 'failed', 'unverified', 'unverified', 'unverified'])

    def test_duplicate_cases_and_incomplete_mapping_are_rejected(self):
        with TemporaryDirectory() as temp:
            report = Path(temp) / 'junit.xml'
            report.write_text('<testsuite><testcase name="one"/><testcase name="one"/></testsuite>',
                              encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                junit_outcomes(report)
        with self.assertRaisesRegex(ValueError, 'exactly'):
            verify_execution('REQ-100 Approve', {}, {'journey::test': 'passed'})

    def test_cli_reports_success_only_after_mapped_checks_pass(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/verify_spec_traceability.py'
        with TemporaryDirectory() as temp:
            root = Path(temp)
            spec, report, mapping = (root / name for name in ('spec.md', 'junit.xml', 'map.json'))
            spec.write_text('REQ-100 Approve exact selection', encoding='utf-8')
            mapping.write_text(json.dumps({'REQ-100': ['journey::approval']}), encoding='utf-8')
            command = [sys.executable, str(script), str(spec), '--assertion-map', str(mapping),
                       '--junit', str(report), '--json']
            for testcase, expected in (('<testcase classname="journey" name="approval"/>', 0),
                                       ('<testcase name="unrelated"/>', 1)):
                report.write_text(f'<testsuite>{testcase}</testsuite>', encoding='utf-8')
                result = subprocess.run(command, capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertEqual(json.loads(result.stdout)['valid'], expected == 0)
