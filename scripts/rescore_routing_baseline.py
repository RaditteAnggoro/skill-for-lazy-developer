"""Derive a routing report after explicitly approved supporting-skill corrections.

This never changes the original report or corpus. Prompts and all other expectations
must remain identical, and wording-grader errors are preserved without inventing text.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import yaml


def rescore(report, old_bytes, new_bytes, allowed):
    if not report.get('complete'):
        raise ValueError('source report is incomplete')
    if hashlib.sha256(old_bytes).hexdigest() != report.get('corpus_sha256'):
        raise ValueError('source corpus digest does not match report')
    old = yaml.safe_load(old_bytes)['cases']
    new = yaml.safe_load(new_bytes)['cases']
    if len(old) != len(new):
        raise ValueError('case count changed')
    changes = {}
    for before, after in zip(old, new):
        before = dict(before); after = dict(after)
        old_support = before.pop('supporting', [])
        new_support = after.pop('supporting', [])
        if before != after:
            raise ValueError('prompt or non-supporting expectation changed')
        if old_support != new_support:
            if before['id'] not in allowed:
                raise ValueError('unapproved expectation change: {}'.format(before['id']))
            changes[before['id']] = {'before': old_support, 'after': new_support}
    if set(changes) != set(allowed):
        raise ValueError('allowed cases do not exactly match changed cases')
    result = json.loads(json.dumps(report))
    for item in result['results']:
        if item['case_id'] not in changes or item['outcome'] == 'blocked':
            continue
        if 'routing' not in item or not isinstance(item['routing'].get('supporting'), list):
            raise ValueError('saved routing evidence missing for {}'.format(item['case_id']))
        errors = [e for e in item['errors'] if not e.startswith('supporting expected ')]
        expected = changes[item['case_id']]['after']
        actual = item['routing']['supporting']
        if expected != actual:
            errors.append('supporting expected {!r}, got {!r}'.format(expected, actual))
        item['errors'] = errors
        item['outcome'] = 'fail' if errors else 'pass'
    result['original_corpus_sha256'] = report['corpus_sha256']
    result['corpus_sha256'] = hashlib.sha256(new_bytes).hexdigest()
    result['expectation_changes'] = changes
    result['derived_rescore'] = True
    result['limitations'].append('Derived rescore of explicitly approved support expectations; original model trials were not rerun and wording errors were retained.')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--old-corpus', type=Path, required=True)
    parser.add_argument('--new-corpus', type=Path, required=True)
    parser.add_argument('--case', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError('output already exists')
        report_bytes = args.report.read_bytes()
        data = rescore(json.loads(report_bytes), args.old_corpus.read_bytes(), args.new_corpus.read_bytes(), set(args.case))
        data['source_report_sha256'] = hashlib.sha256(report_bytes).hexdigest()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, indent=2) + '\n')
        print('Derived report for {} approved cases; original retained'.format(len(data['expectation_changes'])))
        return 0
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        print('Rescore failed: {}'.format(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
