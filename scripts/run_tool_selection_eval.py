"""Evaluate tool-selection instructions against synthetic capability states.

No MCP is invoked. This measures model classification for a supplied mock host,
not real connection, authorization, tool selection at runtime, or task completion.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.run_enhancement_benchmark import (  # noqa: E402
    PROFILE_OPTIONS, benchmark_environment, classify_failure, codex_version,
    isolation_preflight, prepare_router_workspace, snapshot, write_report,
)

SCHEMA = {
    'type': 'object',
    'properties': {'selected': {'type': 'string', 'enum': [
        'native', 'serena', 'context7', 'playwright', 'devtools', 'dbhub', 'github', 'blocked',
    ]}},
    'required': ['selected'], 'additionalProperties': False,
}


def prompt(case):
    """Do not include the expected answer in the agent-visible case."""
    visible = {key: value for key, value in case.items() if key not in ('expected', 'id')}
    return ('Classify this synthetic development scenario by following the repository\'s '
            'adaptive-workflow tool-selection instructions. The host capability facts '
            'below are simulated and are not real connections. Do not install, invoke, '
            'authenticate or configure a provider. Return only the required JSON. '
            'Select native when it is adequate unless the specialized capability gives '
            'a meaningful improvement; select blocked when evidence is required but no '
            'safe capable option exists.\n\nSynthetic case: ' + json.dumps(visible))


def run_case(source, case, codex, model, effort, timeout):
    with tempfile.TemporaryDirectory(prefix='tool-selection-eval-') as tmp:
        work = Path(tmp)
        prepare_router_workspace(source, work)
        schema = work / 'tool-schema.json'; schema.write_text(json.dumps(SCHEMA))
        result = work / 'result.json'
        command = ([codex, 'exec', '--ephemeral', '--ignore-user-config', '--skip-git-repo-check']
                   + PROFILE_OPTIONS + ['--output-schema', str(schema), '--output-last-message', str(result),
                                        '--json', '--cd', str(work), '--model', model,
                                        '-c', 'model_reasoning_effort="{}"'.format(effort)])
        try:
            completed = subprocess.run(command, input=prompt(case), text=True, capture_output=True,
                                       timeout=timeout, env=benchmark_environment(), check=False)
            if completed.returncode:
                return {'outcome': 'blocked', 'reason': classify_failure(completed.stderr)}
            selected = json.loads(result.read_text(encoding='utf-8'))['selected']
            if selected not in SCHEMA['properties']['selected']['enum']:
                raise ValueError('unknown result')
            return {'outcome': 'pass' if selected == case['expected'] else 'fail', 'selected': selected}
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
            return {'outcome': 'blocked', 'reason': type(exc).__name__}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', required=True); parser.add_argument('--patch', type=Path)
    parser.add_argument('--case', action='append', default=[]); parser.add_argument('--trials', type=int, default=3)
    parser.add_argument('--model', required=True); parser.add_argument('--effort', default='high', choices=['low','medium','high','xhigh'])
    parser.add_argument('--codex', default='codex'); parser.add_argument('--timeout', type=int, default=90)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.trials < 3 or args.timeout <= 0:
        parser.error('at least three trials and a positive timeout are required')
    try:
        if args.output.exists(): raise ValueError('output already exists')
        if not isolation_preflight(args.codex): raise ValueError('isolation preflight failed')
        corpus_bytes = (ROOT/'tests/tool_selection_cases.yaml').read_bytes()
        cases = yaml.safe_load(corpus_bytes)['cases']
        if len({case['id'] for case in cases}) != len(cases): raise ValueError('duplicate case ids')
        if args.case:
            by_id = {case['id']:case for case in cases}
            missing = set(args.case)-set(by_id)
            if missing: raise ValueError('unknown cases: {}'.format(', '.join(sorted(missing))))
            cases = [by_id[item] for item in args.case]
        with tempfile.TemporaryDirectory(prefix='tool-selection-source-') as tmp:
            source = Path(tmp); meta = snapshot(args.ref, args.patch, source)
            report = {'scope': 'synthetic tool-choice classification only', 'snapshot': meta,
                      'corpus_sha256': hashlib.sha256(corpus_bytes).hexdigest(),
                      'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      'shared_runner_sha256': hashlib.sha256((ROOT/'scripts/run_enhancement_benchmark.py').read_bytes()).hexdigest(),
                      'model': args.model, 'effort': args.effort, 'codex_version': codex_version(args.codex),
                      'complete': False, 'results': [],
                      'limitations': ['Mock capabilities only; no MCP or real task was invoked.',
                                      'Raw model output and provider token/cost metrics are not retained.']}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            for case in cases:
                for repeat in range(1, args.trials+1):
                    item = run_case(source, case, args.codex, args.model, args.effort, args.timeout)
                    item.update(case_id=case['id'], expected=case['expected'], trial=repeat)
                    report['results'].append(item); write_report(args.output, report)
                    print('{} trial {} {}'.format(case['id'], repeat, item['outcome']), flush=True)
                    if len(report['results']) >= 3 and all(x['outcome']=='blocked' for x in report['results'][-3:]): return 2
            report['complete'] = True; write_report(args.output, report)
            return 0 if all(x['outcome']=='pass' for x in report['results']) else 1
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError, subprocess.CalledProcessError) as exc:
        print('Evaluation setup failed: {}'.format(exc), file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())
