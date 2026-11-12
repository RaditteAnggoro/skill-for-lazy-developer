import hashlib
import unittest

from scripts.rescore_routing_baseline import rescore


class RescoreTests(unittest.TestCase):
    def setUp(self):
        self.old = b'cases:\n- id: ui\n  prompt: same\n  supporting: []\n'
        self.new = b'cases:\n- id: ui\n  prompt: same\n  supporting: [verification-before-completion]\n'
        self.report = {'complete': True, 'corpus_sha256': hashlib.sha256(self.old).hexdigest(),
                       'limitations': [], 'results': [
                           {'case_id': 'ui', 'outcome': 'fail', 'routing': {'supporting': ['verification-before-completion']},
                            'errors': ['supporting expected [], got [verification-before-completion]', 'wording failed']},
                           {'case_id': 'ui', 'outcome': 'blocked', 'errors': ['unavailable']}]}

    def test_only_approved_support_is_rescored_and_original_unchanged(self):
        result = rescore(self.report, self.old, self.new, {'ui'})
        self.assertEqual(result['results'][0]['errors'], ['wording failed'])
        self.assertEqual(result['results'][0]['outcome'], 'fail')
        self.assertEqual(result['results'][1]['outcome'], 'blocked')
        self.assertEqual(len(self.report['results'][0]['errors']), 2)
        self.assertTrue(result['derived_rescore'])

    def test_rejects_prompt_changes_and_unapproved_expectations(self):
        with self.assertRaises(ValueError):
            rescore(self.report, self.old, self.new.replace(b'prompt: same', b'prompt: changed'), {'ui'})
        with self.assertRaises(ValueError):
            rescore(self.report, self.old, self.new, set())
        with self.assertRaises(ValueError):
            rescore(self.report, self.new, self.new, set())


if __name__ == '__main__':
    unittest.main()
