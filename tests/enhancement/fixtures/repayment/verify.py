"""Controlled replay, distinct event, and balance checks for the synthetic fixture."""
import tempfile
import os
import unittest
from pathlib import Path

from ledger import post, postings, setup


class RepaymentTests(unittest.TestCase):
    def test_replay_after_commit_has_one_balanced_effect(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('LAZY_FIXTURE_TMPDIR')) as tmp:
            path = str(Path(tmp) / 'ledger.sqlite')
            setup(path)
            post(path, 'event-1', 125)
            post(path, 'event-1', 125)
            rows = postings(path)
            self.assertEqual(len(rows), 2, 'replay must not duplicate ledger entries')
            self.assertEqual(sum(row[2] for row in rows), 0)
            self.assertEqual({row[1] for row in rows}, {'cash', 'receivable'})

    def test_distinct_events_are_not_deduplicated(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('LAZY_FIXTURE_TMPDIR')) as tmp:
            path = str(Path(tmp) / 'ledger.sqlite')
            setup(path)
            post(path, 'event-1', 125)
            post(path, 'event-2', 125)
            self.assertEqual(len(postings(path)), 4)

    def test_invalid_amount_does_not_post(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('LAZY_FIXTURE_TMPDIR')) as tmp:
            path = str(Path(tmp) / 'ledger.sqlite')
            setup(path)
            with self.assertRaises(ValueError):
                post(path, 'event-1', 0)
            self.assertEqual(postings(path), [])


if __name__ == '__main__':
    unittest.main()
