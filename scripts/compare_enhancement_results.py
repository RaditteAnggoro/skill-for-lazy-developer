"""Compare completed, compatible read-only routing trial reports; no UI or task claims."""
import argparse
import json
from pathlib import Path
import sys

LOCKED = ('scope', 'model', 'effort', 'host', 'python', 'codex_version', 'environment_sha256',
          'runner_sha256', 'scorer_sha256', 'corpus_sha256', 'schema_sha256',
          'permission_profile_sha256', 'network_availability', 'trials', 'case_ids')


def compare(baseline, candidate):
    if not baseline.get('complete') or not candidate.get('complete'):
        raise ValueError('both reports must be complete')
    if any(key not in baseline or key not in candidate for key in LOCKED):
        raise ValueError('report is missing a required configuration lock')
    for key in LOCKED:
        if baseline[key] != candidate[key]:
            raise ValueError('incompatible report: {}'.format(key))
    if baseline.get('isolation_preflight') != 'pass' or candidate.get('isolation_preflight') != 'pass':
        raise ValueError('both reports require isolation preflight')
    expected = {(case, trial) for case in baseline['case_ids']
                for trial in range(1, baseline['trials'] + 1)}
    def select(report, variant):
        rows = [item for item in report['results'] if item['variant'] == variant]
        keyed = {(item['case_id'], item['trial']): item for item in rows}
        if len(keyed) != len(rows) or set(keyed) != expected:
            raise ValueError('missing, duplicate, or unexpected {} trials'.format(variant))
        if any(item['outcome'] not in ('pass', 'fail', 'blocked') for item in rows):
            raise ValueError('unknown trial outcome')
        return keyed
    before = select(baseline, 'baseline')
    after = select(candidate, 'candidate')
    comparable = [key for key in sorted(expected)
                  if before[key]['outcome'] != 'blocked' and after[key]['outcome'] != 'blocked']
    regressions = [list(key) for key in comparable
                   if before[key]['outcome'] == 'pass' and after[key]['outcome'] == 'fail']
    improvements = [list(key) for key in comparable
                    if before[key]['outcome'] == 'fail' and after[key]['outcome'] == 'pass']
    limitations = ['Not an implementation, UI, or safety benchmark.',
                   'Blocked trials are excluded from comparable counts.',
                   'Elapsed time is not compared without a controlled workload.',
                   'Network conditions may be unknown even when settings match.']
    if baseline.get('derived_rescore') or candidate.get('derived_rescore'):
        limitations.append('At least one report was derived by rescoring saved routing choices; inspect the original report and approved expectation changes.')
    return {
        'scope': 'read-only routing comparison',
        'comparable_trials': len(comparable),
        'blocked_or_unpaired_trials': len(expected) - len(comparable),
        'baseline_passes': sum(before[key]['outcome'] == 'pass' for key in comparable),
        'candidate_passes': sum(after[key]['outcome'] == 'pass' for key in comparable),
        'regressions': regressions,
        'improvements': improvements,
        'limitations': limitations,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError('output already exists')
        result = compare(json.loads(args.baseline.read_text()), json.loads(args.candidate.read_text()))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
        print('Compared {} trials; {} blocked; {} regressions'.format(
            result['comparable_trials'], result['blocked_or_unpaired_trials'], len(result['regressions'])))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Comparison failed: {}'.format(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
