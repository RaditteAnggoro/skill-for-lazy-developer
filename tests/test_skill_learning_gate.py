from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

import yaml

from scripts.propose_skill_learning import content_error, duplicate, stage, validate, verify_evidence
from scripts.record_phase_check import record
from scripts.verify_phase_receipts import plan_digest


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tests/learning_proposal_cases.yaml"


class SkillLearningGateTests(unittest.TestCase):
    def setUp(self):
        self.cases = yaml.safe_load(CASES.read_text(encoding="utf-8"))["cases"]

    def test_valid_and_rejected_cases(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                data = case["proposal"]
                errors = validate(data)
                problem = content_error(data) if not errors else None
                duplicate_path = duplicate(data) if not errors and not problem else None
                accepted = not errors and not problem and not duplicate_path
                self.assertEqual(accepted, case["expected"] == "accept", errors + [problem or "", duplicate_path or ""])

    def test_staging_never_touches_active_skills(self):
        data = self.cases[0]["proposal"]
        before = (ROOT / ".agents/skills/ui-implementation/SKILL.md").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            path = stage(data, Path(tmp))
            self.assertTrue(path.is_file())
            self.assertEqual(path.parent, Path(tmp))
        self.assertEqual(before, (ROOT / ".agents/skills/ui-implementation/SKILL.md").read_bytes())

    def test_unknown_fields_and_unobserved_evidence_rejected(self):
        data = dict(self.cases[0]["proposal"])
        data["unexpected"] = "value"
        self.assertTrue(validate(data))
        data = dict(self.cases[1]["proposal"])
        self.assertTrue(validate(data))

    def test_staged_proposal_id_is_immutable(self):
        data = dict(self.cases[0]['proposal'])
        with tempfile.TemporaryDirectory() as tmp:
            path = stage(data, tmp)
            original = path.read_bytes()
            data['why'] = 'A different review rationale'
            with self.assertRaises(FileExistsError):
                stage(data, tmp)
            self.assertEqual(path.read_bytes(), original)

    def test_policy_and_schema_exist(self):
        self.assertTrue((ROOT / ".agents/skills/adaptive-workflow/references/learning-proposal-policy.md").is_file())
        self.assertTrue((ROOT / "docs/schemas/skill_learning_proposal.schema.json").is_file())

    def test_claim_requires_observed_before_and_after_with_same_command(self):
        proposal = deepcopy(self.cases[0]['proposal'])
        item = proposal['evidence'][0]
        check = item['case_id']
        plan = {'phases': [
            dict(id='ui', primary='ui-implementation', entry='ready', exit='run check',
                 evidence='receipt', inputs=['state.txt'], required_checks=[check]),
            dict(id='final', primary='verification-before-completion', entry='ui complete',
                 exit='review', evidence='receipt', inputs=['state.txt'], required_checks=['final'],
                 depends_on=['ui'])]}
        bundle = {'version': 1, 'plan_sha256': plan_digest(plan), 'phases': []}
        command = [sys.executable, '-c', 'raise SystemExit(int(open("state.txt").read()))']
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            item['receipts'] = []
            for code, expected in [('1', 'failed'), ('0', 'passed')]:
                (root/'state.txt').write_text(code, encoding='utf-8')
                self.assertEqual(record(plan, bundle, 'ui', check, root, root, command, 10), expected)
                result = bundle['phases'][0]['checks'][check]
                item['receipts'].append({key: result[key] for key in ('run_id', 'sha256')})
            verify_evidence(proposal, root)
            item['receipts'][0]['sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                verify_evidence(proposal, root)


if __name__ == "__main__":
    unittest.main()
