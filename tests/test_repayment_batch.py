from contextlib import closing
from pathlib import Path
import runpy
import sqlite3
import subprocess
import sys
import tempfile
import unittest


WORKER = Path(__file__).parent / 'enhancement/fixtures/repayment_batch.py'


class RepaymentBatchTests(unittest.TestCase):
    def test_worker_restart_recovers_chunks_and_reconciles_every_event(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / 'batch.sqlite'
            runpy.run_path(str(WORKER))['setup'](database, 751)
            command = [sys.executable, str(WORKER), str(database), '--chunk-size', '128']

            for point, exit_code, applied, postings in (
                ('between-postings', 91, 0, 0), ('after-commit', 92, 128, 256),
                (None, 0, 751, 1502), (None, 0, 751, 1502),
            ):
                with self.subTest(fault=point, expected_applied=applied):
                    fault = ['--crash', point] if point else []
                    result = subprocess.run(command + fault, capture_output=True, timeout=15, check=False)
                    self.assertEqual(result.returncode, exit_code, result.stderr)
                    with closing(sqlite3.connect(database)) as db:
                        self.assertEqual(db.execute('SELECT SUM(applied) FROM staging').fetchone(), (applied,))
                        self.assertEqual(db.execute('SELECT COUNT(*) FROM postings').fetchone(), (postings,))
                        mismatches = db.execute('''
                            SELECT s.event FROM staging s LEFT JOIN postings p ON p.event = s.event
                            GROUP BY s.event
                            HAVING COUNT(p.account) != 2 * s.applied OR COALESCE(SUM(p.amount), 0) != 0
                                OR (s.applied AND (SUM(p.account = 'cash' AND p.amount = s.amount) != 1
                                    OR SUM(p.account = 'receivable' AND p.amount = -s.amount) != 1))
                        ''').fetchall()
                        self.assertEqual(mismatches, [])
