"""Independent synthetic SQLite controls. Keep out of the model's task workspace."""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sqlite3
import tempfile
from threading import Barrier
import unittest

from ledger import post, postings, setup


class DurableRepayment(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=os.environ.get('LAZY_FIXTURE_TMPDIR'))
        self.addCleanup(temporary.cleanup)
        self.path = str(Path(temporary.name) / 'isolated.sqlite')
        setup(self.path)

    def assert_one_effect(self, amount):
        self.assertCountEqual(postings(self.path), [
            ('r1', 'receivable', -amount), ('r1', 'cash', amount),
        ])

    def test_competing_writers_create_one_effect(self):
        start = Barrier(2, timeout=5)

        def writer():
            start.wait()
            post(self.path, 'r1', 125)

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(writer)
            second = pool.submit(writer)
            first.result(timeout=10)
            second.result(timeout=10)
        self.assert_one_effect(125)

    def test_reopened_store_preserves_original_payload(self):
        post(self.path, 'r1', 125)
        setup(self.path)
        post(self.path, 'r1', 125)
        with self.assertRaises(ValueError):
            post(self.path, 'r1', 126)
        self.assert_one_effect(125)

    def test_failed_second_write_rolls_back_and_retry_completes(self):
        # Instrument either write order without dictating which account is written first.
        with sqlite3.connect(self.path) as db:
            db.execute('''CREATE TRIGGER controlled_failure BEFORE INSERT ON postings
                WHEN EXISTS (SELECT 1 FROM postings WHERE event = NEW.event)
                BEGIN SELECT RAISE(ABORT, 'synthetic write failure'); END''')
        with self.assertRaises(Exception):
            post(self.path, 'r1', 125)
        self.assertEqual(postings(self.path), [])
        with sqlite3.connect(self.path) as db:
            db.execute('DROP TRIGGER controlled_failure')
        post(self.path, 'r1', 125)
        self.assert_one_effect(125)


if __name__ == '__main__':
    unittest.main()
