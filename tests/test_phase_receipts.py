from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.verify_phase_receipts import file_digest, plan_digest, verify


class PhaseReceipts(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.artifacts = self.root / 'artifacts'
        self.artifacts.mkdir()
        self.plan = {'task': 'Synthetic two-phase change', 'phases': []}
        for phase, skill, deps in (
            ('work', 'lean-senior-engineering', []),
            ('final', 'verification-before-completion', ['work']),
        ):
            self.plan['phases'].append(dict(id=phase, primary=skill, depends_on=deps,
                                            entry='ready', exit='check passes', evidence='artifact',
                                            inputs=[phase + '.txt'], required_checks=['case']))
            (self.root / (phase + '.txt')).write_text(phase)
            (self.artifacts / (phase + '.log')).write_text('check passed')
        self.bundle = {'version': 1, 'plan_sha256': plan_digest(self.plan), 'phases': []}
        for p in self.plan['phases']:
            file = p['id'] + '.txt'
            artifact = p['id'] + '.log'
            self.bundle['phases'].append(dict(id=p['id'], input_sha256={file: file_digest(self.root, file)},
                                              checks={'case': dict(outcome='passed', path=artifact,
                                                                   sha256=file_digest(self.artifacts, artifact))}))

    def report(self, bundle=None):
        return verify(self.plan, self.bundle if bundle is None else bundle, self.root, self.artifacts)

    def test_complete_receipts_replay_identically(self):
        result = self.report()
        self.assertTrue(result['complete'])
        self.assertEqual(result, self.report())

    def test_predecessor_without_evidence_never_unlocks_dependent_phase(self):
        self.bundle['phases'].pop(0)
        self.assertEqual([row['status'] for row in self.report()['phases']], ['ready', 'waiting'])

    def test_changed_inputs_or_evidence_invalidate_prior_completion(self):
        for filename in (self.root / 'work.txt', self.artifacts / 'work.log'):
            before = filename.read_bytes()
            filename.write_bytes(b'changed')
            self.assertEqual([row['status'] for row in self.report()['phases']], ['stale', 'waiting'])
            filename.write_bytes(before)

    def test_blocked_check_and_missing_artifact_stay_blocked(self):
        blocked = deepcopy(self.bundle)
        blocked['phases'][0]['checks']['case']['outcome'] = 'blocked'
        self.assertEqual([row['status'] for row in self.report(blocked)['phases']], ['blocked', 'waiting'])
        (self.artifacts / 'work.log').unlink()
        self.assertEqual(self.report()['phases'][0]['reason'], 'artifact_unavailable')

    def test_rejects_duplicate_receipts_and_changed_plan(self):
        duplicate = deepcopy(self.bundle)
        duplicate['phases'].append(duplicate['phases'][0])
        with self.assertRaises(ValueError):
            self.report(duplicate)
        self.plan['task'] = 'Different task'
        with self.assertRaises(ValueError):
            self.report()
