import unittest

from scripts.export_enhancement_evidence import convert


class EnhancementEvidenceTests(unittest.TestCase):
    def test_records_do_not_claim_unknown_safety_or_fixture_commit(self):
        report = {
            'scope': 'read-only routing only', 'model': 'example', 'host': 'fixture',
            'corpus_sha256': 'a' * 64,
            'snapshots': {'baseline': {'commit': 'b' * 40}},
            'results': [{'case_id': 'one', 'variant': 'baseline', 'trial': 1,
                         'outcome': 'blocked', 'wall_ms': 100}],
        }
        item = convert(report)[0]
        self.assertEqual(item['outcome'], 'blocked')
        self.assertIsNone(item['safety']['prohibited_egress'])
        self.assertIsNone(item['fixture_commit'])
        self.assertEqual(item['fixture_sha256'], 'a' * 64)
        self.assertIsNone(item['metrics']['context_tokens'])

    def test_rejects_non_routing_report(self):
        with self.assertRaises(ValueError):
            convert({'scope': 'full task evaluation'})


if __name__ == '__main__':
    unittest.main()
