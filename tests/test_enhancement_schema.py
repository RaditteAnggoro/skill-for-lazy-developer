from copy import deepcopy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'docs/schemas/enhancement_run.schema.json').read_text())
EXAMPLE = json.loads((ROOT / 'tests/enhancement/evidence/example-run.json').read_text())


class EnhancementSchemaTests(unittest.TestCase):
    def test_schema_and_example_are_valid(self):
        Draft202012Validator.check_schema(SCHEMA)
        self.assertEqual(list(Draft202012Validator(SCHEMA).iter_errors(EXAMPLE)), [])

    def test_required_fields_and_status_are_checked(self):
        for key in ('case_id', 'outcome', 'safety'):
            example = deepcopy(EXAMPLE)
            del example[key]
            self.assertFalse(Draft202012Validator(SCHEMA).is_valid(example), key)
        example = deepcopy(EXAMPLE)
        example['outcome'] = 'maybe'
        self.assertFalse(Draft202012Validator(SCHEMA).is_valid(example))

    def test_rejects_escaping_evidence_paths(self):
        for path in ('../secret', '/tmp/secret', 'logs/../../secret', 'C:\\secret', 'https://example.com/log'):
            example = deepcopy(EXAMPLE)
            example['checks'][0]['evidence'] = path
            self.assertFalse(Draft202012Validator(SCHEMA).is_valid(example), path)
        example = deepcopy(EXAMPLE)
        example['checks'][0]['evidence'] = 'logs/result.txt'
        self.assertTrue(Draft202012Validator(SCHEMA).is_valid(example))

    def test_null_unknowns_are_allowed_but_negative_counts_are_not(self):
        example = deepcopy(EXAMPLE)
        self.assertTrue(Draft202012Validator(SCHEMA).is_valid(example))
        example['metrics']['context_tokens'] = -1
        self.assertFalse(Draft202012Validator(SCHEMA).is_valid(example))


if __name__ == '__main__':
    unittest.main()
