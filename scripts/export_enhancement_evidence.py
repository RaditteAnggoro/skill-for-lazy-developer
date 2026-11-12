"""Convert routing trial summaries into schema-validated enhancement evidence."""
import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / 'docs/schemas/enhancement_run.schema.json'


def convert(report):
    """Unknown measurements remain null; the digest identifies a dirty corpus."""
    if report.get('scope') != 'read-only routing only':
        raise ValueError('not a routing benchmark report')
    records = []
    for item in report['results']:
        variant = item['variant']
        status = item['outcome']
        checks = [{'id': 'routing-exact-match', 'status': status, 'evidence': None}]
        record = {
            'schema_version': 1,
            'case_id': item['case_id'],
            'variant': variant,
            'repository_commit': report['snapshots'][variant]['commit'],
            'fixture_commit': None,
            'fixture_sha256': report['corpus_sha256'],
            'model': report.get('model'),
            'host': report.get('host', 'not recorded'),
            'tool_availability': {},
            'trial': item['trial'],
            'outcome': status,
            'checks': checks,
            'routing': item.get('routing'),
            'metrics': {'tool_calls': None, 'context_tokens': None, 'wall_ms': item.get('wall_ms')},
            'safety': {'unauthorized_writes': None, 'prohibited_egress': None},
            'limitations': list(report.get('limitations', [])) + [
                'Corpus digest recorded; fixture commit is unknown because the corpus may have local changes.',
                'Raw prompts and model output are not retained in this evidence record.',
            ],
        }
        if not report.get('complete', False):
            record['limitations'].append('Source benchmark is incomplete; this is not a complete corpus result.')
        records.append(record)
    schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
    validator = Draft202012Validator(schema)
    for record in records:
        validator.validate(record)
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError('output already exists')
        report = json.loads(args.report.read_text(encoding='utf-8'))
        records = convert(report)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
        print('Validated {} routing evidence records'.format(len(records)))
        return 0
    except (OSError, KeyError, ValueError, SchemaError, ValidationError) as exc:
        print('Evidence conversion failed: {}'.format(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
