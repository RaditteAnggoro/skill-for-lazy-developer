"""Reproduce context retention and paired live Codex comparisons on synthetic inputs."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.context_optimizer import RawEvidenceStore, compact_case, count_tokens  # noqa: E402
from scripts.run_enhancement_benchmark import (  # noqa: E402
    PROFILE_OPTIONS, benchmark_environment, classify_failure, codex_version, isolation_preflight, write_report,
)

CORPUS = ROOT / 'tests/token_optimization_cases.yaml'
SETTINGS = {'A': (False, False), 'B': (True, False), 'C': (False, True), 'D': (True, True)}
LONG_DEBUG_EVENTS = 900
STRINGS = {'type': 'array', 'items': {'type': 'string'}}
SCHEMA = {'type': 'object', 'required': ['answer', 'evidence', 'constraints'], 'additionalProperties': False,
          'properties': {'answer': {'type': 'string'}, 'evidence': STRINGS, 'constraints': STRINGS}}

LIVE_ORACLES = {
    'long-ledger': ('ERROR BATCH-19 partially committed after debit step',
                    'missing commit marker for batch BATCH-19', 'replay must preserve batch ID and idempotent entries'),
    'short-invoice': ('ERROR INV-1042 amount mismatch detected at reconciliation step',
                      'cause: stale FX cache reused a previous rate', 'fix: clear FX cache, preserve invoice row, then retry'),
}


def packets(case, path):
    store = RawEvidenceStore(path)
    return {arm: compact_case({**case, 'source_kind': 'captured_snippets'}, store, retrieve=retrieval, compact=compression)
            for arm, (retrieval, compression) in SETTINGS.items()}


def score(case, answer, constraints, evidence):
    eligible = {item.strip() for item in constraints}
    observed = {item.strip() for item in evidence}
    expected = set(LIVE_ORACLES[case['id']])
    facts = sum(fact.casefold() in (answer + '\n' + '\n'.join(evidence)).casefold() for fact in case['must_include'])
    return {'facts': facts, 'required_quotes': len(observed & expected), 'constraints_exact':
            eligible == {value.strip() for value in case['constraints']},
            'answer_nonempty': bool(answer.strip())}


def local_cases(cases):
    rows = []
    with tempfile.TemporaryDirectory(prefix='ld-context-static-') as tmp:
        path = Path(tmp)
        for case in cases:
            values = packets(case, path)
            store = RawEvidenceStore(path)
            row = {'id': case['id'], 'arms': {}}
            for arm, packet in values.items():
                text = packet['optimized']
                row['arms'][arm] = {'tokens': count_tokens(text)[0],
                    'facts_preserved': all(fact.casefold() in text.casefold() for fact in case['must_include']),
                    'constraints_preserved': all(rule in text for rule in case['constraints']),
                    'evidence_recovered': store.get(packet['raw_refs'][0]) == packet['raw_tool']
                        and store.get(packet['raw_refs'][1]) == packet['raw_source']}
            row['reduction_percent'] = 100 * (1 - row['arms']['D']['tokens'] / row['arms']['A']['tokens'])
            rows.append(row)
    return rows


def live_case(case, context, codex, model, effort, timeout):
    with tempfile.TemporaryDirectory(prefix='ld-context-live-') as tmp:
        workspace = Path(tmp)
        schema, result = workspace / 'schema.json', workspace / 'result.json'
        schema.write_text(json.dumps(SCHEMA), encoding='utf-8')
        cmd = [codex, 'exec', '--ephemeral', '--ignore-user-config', '--skip-git-repo-check', *PROFILE_OPTIONS,
               '--disable', 'shell_tool',
               '--json', '--cd', str(workspace), '--model', model, '-c', f'model_reasoning_effort="{effort}"',
               '--output-schema', str(schema), '--output-last-message', str(result)]
        prompt = ('Answer this synthetic closed-book task using only the packet below. '
                  'In answer provide the affected record ID, the cause, and a safe next step. '
                  'In evidence quote the three complete observation lines which establish the error, its cause '
                  'or missing prerequisite, and the prescribed recovery or replay behavior. '
                  'Copy every line under Constraints or CRITICAL CONSTRAINTS verbatim into constraints. '
                  'Keep punctuation, and omit headings from values. Use no tools.\n\n' + context)
        started = time.monotonic()
        try:
            done = subprocess.run(cmd, input=prompt, text=True, capture_output=True, check=False, timeout=timeout,
                                  env=benchmark_environment())
            seconds = round(time.monotonic() - started, 3)
            if done.returncode:
                return {'status': 'blocked', 'reason': classify_failure(done.stderr), 'seconds': seconds}
            answer = json.loads(result.read_text(encoding='utf-8'))
            events = [json.loads(line) for line in done.stdout.splitlines() if line.startswith('{')]
            usage = next((event.get('usage') for event in reversed(events) if event.get('type') == 'turn.completed'), None)
            calls = sum(event.get('type') == 'item.completed' and (event.get('item') or {}).get('type') in
                        {'command_execution', 'mcp_tool_call'} for event in events)
            checks = score(case, answer['answer'], answer['constraints'], answer['evidence'])
            passed = (checks['facts'] == len(case['must_include']) and checks['required_quotes'] == len(LIVE_ORACLES[case['id']])
                      and checks['constraints_exact'] and checks['answer_nonempty'] and calls == 0)
            return {'status': 'pass' if passed else 'fail', 'checks': checks,
                    'usage': usage, 'tool_calls': calls, 'seconds': seconds,
                    'context_tokens_estimate': count_tokens(context)[0]}
        except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
            return {'status': 'blocked', 'reason': type(exc).__name__, 'seconds': round(time.monotonic() - started, 3)}


def paired_metrics(rows, task):
    pairs = {}
    for row in rows:
        if row['case'] == task and row['status'] != 'blocked' and isinstance(row.get('usage'), dict):
            pairs.setdefault(row['round'], {})[row['arm']] = row
    reductions = []
    for arms in pairs.values():
        if {'A', 'D'} <= arms.keys():
            baseline, candidate = arms['A']['usage'].get('input_tokens'), arms['D']['usage'].get('input_tokens')
            if type(baseline) is int and baseline > 0 and type(candidate) is int:
                reductions.append(round(100 * (1 - candidate / baseline), 2))
    return {'matched_rounds': len(reductions), 'paired_input_reductions_percent': reductions,
            'median_input_reduction_percent': statistics.median(reductions) if reductions else None}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--model')
    parser.add_argument('--effort', default='low', choices=['low', 'medium', 'high', 'xhigh'])
    parser.add_argument('--codex', default='codex')
    parser.add_argument('--trials', type=int, default=3)
    parser.add_argument('--timeout', type=int, default=100)
    args = parser.parse_args(argv)
    if args.live and (not args.model or args.trials < 3 or args.timeout < 1):
        parser.error('live comparison needs an explicit model, positive timeout, and at least three trials')
    if args.output.exists():
        parser.error('choose a new output path')
    cases = yaml.safe_load(CORPUS.read_bytes())['cases']
    local = local_cases(cases)
    median = round(statistics.median(row['reduction_percent'] for row in local), 2)
    report = {'schema_version': 1, 'legacy_baseline_git': '66b12c368364ee5ae78add552ad87ac349248a11',
              'source_sha256': {name: hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest()
                                for name in ('context_optimizer.py', 'run_context_intelligence_benchmark.py', 'run_enhancement_benchmark.py')},
              'corpus_sha256': hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
              'local': local, 'median_packed_reduction_percent': median, 'live': [], 'complete': False}
    report['local_gate_pass'] = median >= 30 and all(all(value for key, value in row['arms']['D'].items() if key != 'tokens') for row in local)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_report(args.output, report)
    if args.live:
        if not isolation_preflight(args.codex):
            report['live_reason'] = 'isolation_preflight_failed'
            write_report(args.output, report)
            return 2
        report.update(model=args.model, host=codex_version(args.codex), effort=args.effort, timeout=args.timeout,
                      rounds=args.trials, concurrent_arms=4, long_debug_events=LONG_DEBUG_EVENTS,
                      profile_sha256=hashlib.sha256('\n'.join([*PROFILE_OPTIONS, '--disable', 'shell_tool']).encode()).hexdigest())
        by_id = {case['id']: case for case in cases}
        short = {**by_id['invoice-reconcile'], 'id': 'short-invoice'}
        repeats = '\n'.join(f'debug: worker heartbeat worker=W{index % 32:02d} sequence={index:05d} state=idle'
                            for index in range(LONG_DEBUG_EVENTS))
        long = {**by_id['ledger-batch'], 'id': 'long-ledger',
                'tool_output': repeats + '\n' + by_id['ledger-batch']['tool_output']}
        with tempfile.TemporaryDirectory(prefix='ld-context-benchmark-') as tmp, ThreadPoolExecutor(max_workers=4) as pool:
            for case, arms in ((long, 'ABCD'), (short, 'AD')):
                contexts = {arm: value['optimized'] for arm, value in packets(case, Path(tmp)).items()}
                report.setdefault('contexts', {})[case['id']] = {
                    arm: hashlib.sha256(text.encode()).hexdigest() for arm, text in contexts.items()}
                if case is long:
                    smoke = [pool.submit(live_case, case, contexts['A'], args.codex, args.model, args.effort, args.timeout)
                             for _ in range(2)]
                    report['aa_smoke'] = [future.result() for future in smoke]
                    write_report(args.output, report)
                    print('A/A', [item['status'] for item in report['aa_smoke']], flush=True)
                for round_id in range(1, args.trials + 1):
                    offset = (round_id - 1) % len(arms)
                    ordered = arms[offset:] + arms[:offset]
                    trials = [pool.submit(live_case, case, contexts[arm], args.codex, args.model, args.effort, args.timeout)
                              for arm in ordered]
                    for arm, future in zip(ordered, trials):
                        observed = future.result()
                        report['live'].append({'case': case['id'], 'round': round_id, 'arm': arm, **observed})
                        write_report(args.output, report)
                        print(case['id'], round_id, arm, observed['status'], flush=True)
        report['comparison'] = {case['id']: paired_metrics(report['live'], case['id']) for case in (long, short)}
        report['answer_gate_pass'] = (all(item['status'] == 'pass' for item in report['live'])
                                      and all(item['status'] == 'pass' for item in report['aa_smoke']))
        long_evidence = report['comparison']['long-ledger']
        report['long_provider_target_met'] = (report['answer_gate_pass'] and long_evidence['matched_rounds'] == args.trials
                                               and long_evidence['median_input_reduction_percent'] >= 30)
    report['complete'] = True
    write_report(args.output, report)
    print(json.dumps({key: value for key, value in report.items() if key in {
        'median_packed_reduction_percent', 'local_gate_pass', 'comparison', 'answer_gate_pass', 'long_provider_target_met'}}, indent=2))
    return 0 if report['local_gate_pass'] and report.get('answer_gate_pass', True) else 1


if __name__ == '__main__':
    sys.exit(main())
