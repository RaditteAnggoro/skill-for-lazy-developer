from copy import deepcopy
import unittest

from scripts.compare_enhancement_results import LOCKED, compare


def report(variant, outcomes):
    result = {key: 'same' for key in LOCKED}
    result.update(scope='read-only routing only', trials=3, case_ids=['one'],
                  complete=True, isolation_preflight='pass')
    result['results'] = [dict(case_id='one', variant=variant, trial=i, outcome=outcome)
                         for i, outcome in enumerate(outcomes, 1)]
    return result


class ComparisonTests(unittest.TestCase):
    def test_counts_regressions_and_excludes_blocked(self):
        a = report('baseline', ['pass', 'fail', 'blocked'])
        b = report('candidate', ['fail', 'pass', 'pass'])
        value = compare(a, b)
        self.assertEqual(value['comparable_trials'], 2)
        self.assertEqual(value['blocked_or_unpaired_trials'], 1)
        self.assertEqual(value['coverage_status'], 'partial')
        self.assertEqual(value['blocked_by_variant'], {'baseline': 1, 'candidate': 0})
        self.assertEqual(value['regressions'], [['one', 1]])
        self.assertEqual(value['improvements'], [['one', 2]])

    def test_mismatched_or_incomplete_runs_are_rejected(self):
        a = report('baseline', ['pass'] * 3)
        b = report('candidate', ['pass'] * 3)
        changed = deepcopy(b); changed['corpus_sha256'] = 'different'
        with self.assertRaises(ValueError): compare(a, changed)
        changed = deepcopy(b); changed['complete'] = False
        with self.assertRaises(ValueError): compare(a, changed)
        changed = deepcopy(b); changed['results'].pop()
        with self.assertRaises(ValueError): compare(a, changed)
        changed = deepcopy(b); changed['isolation_preflight'] = 'unknown'
        with self.assertRaises(ValueError): compare(a, changed)

    def test_derived_baseline_is_disclosed(self):
        a = report('baseline', ['pass'] * 3); a['derived_rescore'] = True
        b = report('candidate', ['pass'] * 3)
        self.assertTrue(any('rescoring' in x for x in compare(a, b)['limitations']))

    def test_missing_case_coverage_is_insufficient(self):
        a = report('baseline', ['blocked'] * 3)
        b = report('candidate', ['pass'] * 3)
        value = compare(a, b)
        self.assertEqual(value['coverage_status'], 'insufficient_evidence')
        self.assertEqual(value['uncovered_case_ids'], ['one'])
        self.assertEqual(value['comparable_trials'], 0)
        self.assertEqual(value['scheduled_pairs'], 3)

    def test_empty_corpus_is_invalid(self):
        a = report('baseline', ['pass'] * 3)
        b = report('candidate', ['pass'] * 3)
        for variant in (a, b):
            variant.update(case_ids=[], results=[])
        with self.assertRaises(ValueError):
            compare(a, b)


if __name__ == '__main__':
    unittest.main()
