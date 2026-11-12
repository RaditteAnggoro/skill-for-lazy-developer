from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EnhancementFixtureTests(unittest.TestCase):
    def test_repayment_fixture_reproduces_the_declared_replay_bug(self):
        fixture = ROOT / 'tests/enhancement/fixtures/repayment'
        result = subprocess.run([sys.executable, 'verify.py'], cwd=fixture,
                                capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('test_replay_after_commit_has_one_balanced_effect', result.stderr)
        self.assertIn('FAILED (failures=1)', result.stderr)
        self.assertIn('Ran 3 tests', result.stderr)

    @unittest.skipUnless(shutil.which('java') and shutil.which('javac'), 'Java compiler/runtime unavailable')
    def test_java_fixture_reproduces_replay_without_hiding_other_checks(self):
        fixture = ROOT / 'tests/enhancement/fixtures/java-repayment'
        with tempfile.TemporaryDirectory() as tmp:
            compiled = subprocess.run(['javac', '-d', tmp, str(fixture/'PostingService.java'),
                                       str(fixture/'Verifier.java')], capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run(['java', '-cp', tmp, 'Verifier'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('FAIL replay must produce two entries', result.stderr)
            self.assertIn('PASS distinct events', result.stdout)
            self.assertIn('PASS ledger balance', result.stdout)


if __name__ == '__main__':
    unittest.main()
