from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.scan_skill_security import MAX_TEXT_BYTES, scan_path, scan_text, verdict


class SecurityScanBoundaries(unittest.TestCase):
    def test_symlink_is_reported_without_reading_its_target(self):
        with TemporaryDirectory() as temp:
            directory = Path(temp)
            bundle = directory / 'bundle'
            bundle.mkdir()
            note = directory / 'unrelated.md'
            note.write_text('A benign note outside the fixture.', encoding='utf-8')
            link = bundle / 'pointer.md'
            try:
                link.symlink_to(note)
            except OSError as exc:
                self.skipTest(str(exc))
            for path in (bundle, link):
                findings = scan_path(path)
                self.assertEqual([row['rule'] for row in findings], ['symlink-not-scanned'])
                self.assertEqual(verdict(findings), 'review')

    def test_sources_in_findings_are_redacted(self):
        findings = scan_text('sudo echo synthetic-private-note')
        self.assertEqual(findings[0]['rule'], 'broad-permissions')
        self.assertNotIn('synthetic-private-note', str(findings))

    def test_unreadable_text_formats_are_marked_for_review(self):
        with TemporaryDirectory() as temp:
            bundle = Path(temp)
            (bundle / 'binary.md').write_bytes(b'\x00\xff')
            (bundle / 'large.md').write_bytes(b'x' * (MAX_TEXT_BYTES + 1))
            findings = scan_path(bundle)
            self.assertEqual({row['rule'] for row in findings}, {'binary-not-scanned', 'size-limit'})
            self.assertEqual(verdict(findings), 'review')
