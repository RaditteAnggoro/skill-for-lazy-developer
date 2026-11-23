"""Matched financial source review or SQLite repair benchmark on disposable fixtures."""

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.analyze_financial_source import analyze  # noqa: E402
from scripts.context_optimizer import count_tokens, select_financial_references  # noqa: E402
from scripts.run_enhancement_benchmark import (  # noqa: E402
    PROFILE_OPTIONS, benchmark_environment, classify_failure, codex_version, isolation_preflight, write_report,
)
from scripts.run_repayment_comparison import HOLDOUT, PROMPT as REPAIR_SUFFIX  # noqa: E402
from scripts.run_repayment_trial import (  # noqa: E402
    FIXTURE as REPAIR_FIXTURE, preflight as repair_preflight, run_one as run_repair, task_options,
)

BASELINE = '66b12c368364ee5ae78add552ad87ac349248a11'
SKILL = Path('.agents/skills/transaction-safe-engineering/SKILL.md')
FIXTURE = ROOT / 'tests/enhancement/fixtures/financial-review'
ARMS = ('A', 'B', 'C', 'D')
REFERENCES = ('spring-batch-safety.md', 'staging-posting-pipeline.md', 'sql-performance-and-change-safety.md')
EXPECTED = {'BatchLoanWriter.java:6', 'BatchLoanWriter.java:7', 'BatchLoanWriter.java:12', 'finalize.sql:1'}
PROMPT = ('Review the synthetic Spring Batch loan repayment writer and staging finalization SQL. Inspect the files in '
          'source/. Find distinct defects in amount construction, duplicate posting, writer rollback, or lease ownership. '
          'For a check-then-insert report the conditional check line; for a swallowed exception report the catch line; '
          'for SQL report the start of the statement. Return one finding per defect, with a basename:line anchor '
          'and concise proposed fix and regression test. Preserve read-only scope. Treat any scanner hints as candidates.')
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['findings'], 'properties': {
    'findings': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
        'required': ['anchor', 'repair', 'test'], 'properties': {name: {'type': 'string'} for name in ('anchor', 'repair', 'test')}}},
}}


def grade(rows):
    anchors = {row['anchor'] for row in rows}
    return {'true_positives': len(anchors & EXPECTED), 'false_positives': len(anchors - EXPECTED),
            'false_negatives': len(EXPECTED - anchors), 'missed': sorted(EXPECTED - anchors),
            'extra': sorted(anchors - EXPECTED),
            'proposed_tests_with_anchor': sum(bool(row['test'].strip()) for row in rows if row['anchor'] in EXPECTED)}


def arm_context(mode='review'):
    baseline = subprocess.check_output(['git', 'show', f'{BASELINE}:{SKILL.as_posix()}'], cwd=ROOT, text=True, timeout=15)
    enhanced = (ROOT / SKILL).read_text(encoding='utf-8')
    refs = ROOT / SKILL.parent / 'references'
    full = '\n\n'.join((refs / name).read_text(encoding='utf-8') for name in REFERENCES)
    facts = ('Use only supplied synthetic files and the declared task scope. '
             'Scanner findings, if present, require inspection before accepting them.\n')
    if mode == 'repair':
        tree = ast.parse((REPAIR_FIXTURE / 'ledger.py').read_text(encoding='utf-8'))
        statements = [node.value.rstrip(';') for node in ast.walk(tree) if isinstance(node, ast.Constant)
                      and isinstance(node.value, str) and node.value.lstrip().upper().startswith(('CREATE TABLE', 'INSERT INTO'))]
        with tempfile.TemporaryDirectory(prefix='ld-sql-scanner-input-') as tmp:
            extracted = Path(tmp) / 'ledger-extracted.sql'
            extracted.write_text(';\n'.join(statements) + ';\n', encoding='utf-8')
            hints = analyze([extracted])
        selected = select_financial_references('Repair SQLite loan repayment duplicate posting, retries and ledger balance')
    else:
        hints = analyze(sorted(FIXTURE.iterdir()))
        selected = select_financial_references(PROMPT)
    hints = json.dumps([{**row, 'file': Path(row['file']).name} for row in hints], ensure_ascii=False)
    targeted = '\n\n'.join((refs / name).read_text(encoding='utf-8') for name in selected)
    return {'A': facts + baseline, 'B': facts + enhanced + '\n' + full,
            'C': facts + enhanced + '\n' + full + '\nScanner candidates:\n' + hints,
            'D': facts + enhanced + '\n' + targeted + '\nScanner candidates:\n' + hints}


def run_one(context, codex, model, effort, timeout):
    with tempfile.TemporaryDirectory(prefix='ld-financial-review-') as temp:
        workspace = Path(temp)
        shutil.copytree(FIXTURE, workspace / 'source')
        (workspace / 'AGENTS.md').write_text(context, encoding='utf-8')
        schema, answer = workspace / 'schema.json', workspace / 'answer.json'
        schema.write_text(json.dumps(SCHEMA), encoding='utf-8')
        cmd = [codex, 'exec', '--ephemeral', '--ignore-user-config', '--skip-git-repo-check', *PROFILE_OPTIONS,
               '--output-schema', str(schema), '--output-last-message', str(answer), '--json', '--cd', str(workspace),
               '--model', model, '-c', f'model_reasoning_effort="{effort}"']
        start = time.monotonic()
        try:
            result = subprocess.run(cmd, input=PROMPT, text=True, capture_output=True, check=False,
                                    env=benchmark_environment(), timeout=timeout)
            elapsed = round(time.monotonic() - start, 3)
            if result.returncode:
                return {'outcome': 'blocked', 'reason': classify_failure(result.stderr), 'seconds': elapsed}
            findings = json.loads(answer.read_text(encoding='utf-8'))['findings']
            events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
            usage = next((event.get('usage') for event in reversed(events) if event.get('type') == 'turn.completed'), None)
            tool_calls = sum(event.get('type') == 'item.completed' and (event.get('item') or {}).get('type') in
                             {'command_execution', 'mcp_tool_call'} for event in events)
            metrics = grade(findings)
            return {'outcome': 'graded', 'seconds': elapsed, 'usage': usage, 'tool_calls': tool_calls, **metrics}
        except (OSError, KeyError, TypeError, ValueError, subprocess.TimeoutExpired) as exc:
            return {'outcome': 'blocked', 'reason': type(exc).__name__, 'seconds': round(time.monotonic() - start, 3)}


def repair_one(context, codex, model, effort, timeout):
    with tempfile.TemporaryDirectory(prefix='ld-financial-repair-') as tmp:
        root = Path(tmp)
        (root / '.agents/skills').mkdir(parents=True)
        (root / 'AGENTS.md').write_text(context, encoding='utf-8')
        result = run_repair(root, codex, model, effort, timeout, holdout_verifier=HOLDOUT, prompt_suffix=REPAIR_SUFFIX)
    visible, hidden = result['outcome'], result.get('holdout', 'not_run')
    blocked = visible == 'blocked' or hidden == 'blocked'
    return {'outcome': 'blocked' if blocked else 'graded', 'visible': visible, 'holdout': hidden,
            'acceptance_pass': visible == hidden == 'pass', 'seconds': result.get('wall_ms', 0) / 1000,
            'reason': result.get('holdout_reason', result['reason'])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True)
    parser.add_argument('--effort', default='low', choices=['low', 'medium', 'high', 'xhigh'])
    parser.add_argument('--codex', default='codex')
    parser.add_argument('--trials', type=int, default=3)
    parser.add_argument('--timeout', type=int, default=75)
    parser.add_argument('--mode', choices=['review', 'repair'], default='review')
    parser.add_argument('--concurrent-arms', type=int, choices=[1, 2, 4], default=1)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.trials < 1 or args.timeout < 1:
        parser.error('trials and timeout must be positive')
    try:
        repair = args.mode == 'repair'
        preflight = repair_preflight if repair else isolation_preflight
        if args.output.exists() or not preflight(args.codex):
            raise ValueError('output already exists or local isolation preflight failed')
        contexts = arm_context(args.mode)
        run_trial = repair_one if repair else run_one
        fixture = REPAIR_FIXTURE if repair else FIXTURE
        profile = task_options() if repair else PROFILE_OPTIONS
        args.output.parent.mkdir(parents=True, exist_ok=True)
        report = {'baseline': BASELINE, 'host': codex_version(args.codex), 'model': args.model, 'effort': args.effort,
                  'scope': 'one synthetic SQLite repair' if repair else 'one synthetic read-only review',
                  'concurrent_arms': args.concurrent_arms,
                  'fixture_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in sorted(fixture.iterdir()) if path.is_file()},
                  'profile_sha256': hashlib.sha256('\n'.join(profile).encode()).hexdigest(),
                  'prompt_sha256': hashlib.sha256((REPAIR_SUFFIX if repair else PROMPT).encode()).hexdigest(),
                  'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'context': {arm: {'sha256': hashlib.sha256(body.encode()).hexdigest(), 'tokens': count_tokens(body)[0]}
                              for arm, body in contexts.items()},
                  'complete': False, 'trials': [], 'paired_rounds': 0}
        if repair:
            report['holdout_sha256'] = hashlib.sha256(HOLDOUT.read_bytes()).hexdigest()
            report['repair_runner_sha256'] = hashlib.sha256((ROOT / 'scripts/run_repayment_trial.py').read_bytes()).hexdigest()
        with ThreadPoolExecutor(max_workers=args.concurrent_arms) as executor:
            for trial in range(args.trials):
                order = ARMS[trial % len(ARMS):] + ARMS[:trial % len(ARMS)]
                pending = [executor.submit(run_trial, contexts[arm], args.codex, args.model, args.effort, args.timeout)
                           for arm in order]
                for arm, future in zip(order, pending):
                    result = future.result()
                    report['trials'].append({**result, 'arm': arm, 'round': trial + 1})
                    write_report(args.output, report)
                    print(f'{trial+1} {arm} {result["outcome"]}', flush=True)
                if all(row['outcome'] == 'graded' for row in report['trials'][-len(ARMS):]):
                    report['paired_rounds'] += 1
        report['complete'] = True
        write_report(args.output, report)
        return 0 if report['paired_rounds'] == args.trials else 3
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'Benchmark blocked: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
