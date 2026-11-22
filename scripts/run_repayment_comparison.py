"""Compare frozen instruction snapshots on one isolated synthetic repayment task."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.run_enhancement_benchmark import benchmark_environment, codex_version, write_report  # noqa: E402
from scripts.run_repayment_trial import fixture_digest, preflight, run_one, task_options  # noqa: E402

BASELINE = '47d09764639a142026c42aec7985deadc0af24d7'
UPSTREAM = '22f0b463e7a5e579904dd6211a520321035526f7'
SKILLS = ('systematic-debugging', 'verification-before-completion')
HOLDOUT = ROOT / 'tests/enhancement/fixtures/repayment_holdout.py'
PROMPT = (' Protect against concurrent retries. Persist the original effect across reopening the database, '
          'reject an existing event with a different amount using ValueError, and keep both writes atomic '
          'if either write fails. Preserve the existing SQLite postings table and public functions. '
          'Use the workflow marked for this task in AGENTS.md.')


def summarize(results, variants):
    """Compare acceptance only on rounds where all three arms completed grading."""
    by_trial = {}
    for row in results:
        trial = by_trial.setdefault(row['trial'], {})
        if row['variant'] in trial:
            raise ValueError('duplicate benchmark trial')
        outcome = row['outcome']
        trial[row['variant']] = row.get('holdout', 'blocked') if outcome == 'pass' else outcome
    matched = [row for row in by_trial.values()
               if set(row) == set(variants) and all(state in {'pass', 'fail'} for state in row.values())]
    passes = {variant: sum(row[variant] == 'pass' for row in matched) for variant in variants}
    status = 'insufficient_evidence'
    if len(matched) >= 3:
        status = 'below_upstream' if passes['candidate'] < passes['superpowers'] else 'matched_or_above_on_fixture'
    return {'matched_trials': len(matched), 'passes': passes, 'status': status}


def git_show(repo, revision, path):
    return subprocess.check_output(['git', 'show', f'{revision}:{path}'], cwd=repo, timeout=15)


def instructions(target, variant, upstream):
    shared = ('Use the applicable skill instructions below as workflow guidance. Only local synthetic fixture '
              'files are in scope. Do not install software, access other projects, call external tools, '
              'or start workers outside this session. Read these skill files before working:\n\n')
    names = SKILLS if variant == 'superpowers' else ('transaction-safe-engineering', *SKILLS)
    paths = []
    for name in names:
        path = Path('.agents/skills') / name / 'SKILL.md'
        file = target / path
        file.parent.mkdir(parents=True)
        if variant == 'superpowers':
            data = git_show(upstream, UPSTREAM, f'skills/{name}/SKILL.md')
        elif variant == 'baseline':
            data = git_show(ROOT, BASELINE, path.as_posix())
        else:
            data = (ROOT / path).read_bytes()
        file.write_bytes(data)
        paths.append(path.as_posix())
    (target / 'AGENTS.md').write_text(shared + ''.join(f'- {path}\n' for path in paths), encoding='utf-8')
    if variant == 'superpowers':
        # Upstream code is never executed; retain its license by the temporary snapshot.
        (target / '.agents/skills/LICENSE').write_bytes(git_show(upstream, UPSTREAM, 'LICENSE'))
    return {path: hashlib.sha256((target / path).read_bytes()).hexdigest()
            for path in ['AGENTS.md', *paths]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--effort', default='medium', choices=('low', 'medium', 'high', 'xhigh'))
    parser.add_argument('--timeout', type=int, default=120)
    parser.add_argument('--codex', default='codex')
    args = parser.parse_args(argv)
    if args.timeout < 1:
        parser.error('timeout must be positive')
    variants = ['baseline', 'superpowers', 'candidate']
    try:
        if args.output.exists():
            raise ValueError('report already exists')
        origin = subprocess.check_output(['git', 'remote', 'get-url', 'origin'], cwd=args.upstream,
                                         text=True, timeout=15).strip().removesuffix('.git')
        if origin.casefold() != 'https://github.com/obra/superpowers':
            raise ValueError('expected the pinned public Superpowers clone')
        if not preflight(args.codex):
            raise ValueError('isolation preflight failed; no trials run')
        report = {'scope': 'one synthetic SQLite repair; selected skills, not complete packages',
                  'baseline': BASELINE, 'upstream': UPSTREAM, 'model': args.model,
                  'effort': args.effort, 'host_cli': codex_version(args.codex),
                  'fixture_sha256': fixture_digest(), 'holdout_sha256': hashlib.sha256(HOLDOUT.read_bytes()).hexdigest(),
                  'runner_sha256': {name: hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest()
                                    for name in ('run_repayment_comparison.py', 'run_repayment_trial.py',
                                                 'run_enhancement_benchmark.py')},
                  'profile_sha256': hashlib.sha256('\n'.join(task_options()).encode()).hexdigest(),
                  'environment_sha256': hashlib.sha256(json.dumps(benchmark_environment(), sort_keys=True).encode()).hexdigest(),
                  'prompt_suffix': PROMPT, 'trials': 3, 'results': [], 'complete': False}
        with tempfile.TemporaryDirectory(prefix='ld-repayment-compare-') as tmp:
            root = Path(tmp)
            report['instruction_sha256'] = {v: instructions(root/v, v, args.upstream) for v in variants}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            for i in range(3):
                for variant in variants[i:] + variants[:i]:
                    result = run_one(root/variant, args.codex, args.model, args.effort, args.timeout,
                                     holdout_verifier=HOLDOUT, prompt_suffix=PROMPT)
                    result.update(trial=i+1, variant=variant)
                    report['results'].append(result)
                    write_report(args.output, report)
                    print(variant, i+1, result['outcome'], result.get('holdout', 'not_run'), flush=True)
                    if all(row['outcome'] == 'blocked' for row in report['results'][-3:]) and len(report['results']) >= 3:
                        return 2
        report['complete'] = True
        report['comparison'] = summarize(report['results'], variants)
        write_report(args.output, report)
        status = report['comparison']['status']
        return {'matched_or_above_on_fixture': 0, 'below_upstream': 1, 'insufficient_evidence': 3}[status]
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'Comparison blocked: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
