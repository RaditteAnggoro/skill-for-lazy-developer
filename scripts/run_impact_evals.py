"""Measure source-file recall/precision on a synthetic read-only impact fixture.

Only the fixture source is visible to the model; ground truth remains outside its
workspace. This does not measure runtime correctness, Java/Spring, or real repositories.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import shutil
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

CASES = ROOT/'tests/enhancement/impact_cases.yaml'
FIXTURE = ROOT/'tests/enhancement/fixtures/impact'
SCHEMA = {'type': 'object', 'properties': {'files': {'type': 'array',
          'items': {'type': 'string'}}}, 'required': ['files'], 'additionalProperties': False}


def fixture_hash():
    digest = hashlib.sha256()
    for path in sorted(FIXTURE.iterdir()):
        if path.is_symlink() or not path.is_file():
            raise ValueError('fixture contains a non-regular file')
        data = path.read_bytes()
        digest.update(path.name.encode() + b'\0' + len(data).to_bytes(8, 'big') + data)
    return digest.hexdigest()


def score(actual, expected):
    actual, expected = set(actual), set(expected)
    if not expected:
        raise ValueError('empty ground truth')
    overlap = len(actual & expected)
    return {'recall': overlap/len(expected),
            'precision': overlap/len(actual) if actual else 0.0,
            'missing': sorted(expected-actual), 'extra': sorted(actual-expected)}


def run_case(source, case, codex, model, effort, timeout):
    with tempfile.TemporaryDirectory(prefix='impact-eval-') as tmp:
        work = Path(tmp); prepare_router_workspace(source, work)
        shutil.copytree(FIXTURE, work/'project')
        schema = work/'schema.json'; schema.write_text(json.dumps(SCHEMA))
        result = work/'result.json'
        command = ([codex, 'exec', '--ephemeral', '--ignore-user-config', '--skip-git-repo-check']
                   + PROFILE_OPTIONS + ['--output-schema',str(schema),'--output-last-message',str(result),
                                        '--json','--cd',str(work),'--model',model,
                                        '-c','model_reasoning_effort="{}"'.format(effort)])
        prompt = ('This is an analysis-only synthetic project in the project/ directory. '
                  'Inspect source and apply the repository instructions. Do not edit files or invoke external services. '
                  'Return only the required JSON with source file basenames, not directory paths.\n\n'
                  + case['prompt'])
        try:
            completed = subprocess.run(command, input=prompt, text=True, capture_output=True,
                                       timeout=timeout, env=benchmark_environment(), check=False)
            if completed.returncode:
                return {'outcome':'blocked','reason':classify_failure(completed.stderr)}
            actual = json.loads(result.read_text(encoding='utf-8'))['files']
            if not isinstance(actual,list) or not all(isinstance(x,str) for x in actual):
                raise ValueError('invalid file list')
            if len(set(actual)) != len(actual): raise ValueError('duplicate filenames')
            metrics = score(actual, case['files'])
            metrics['outcome'] = 'pass' if metrics['recall'] == metrics['precision'] == 1 else 'fail'
            return metrics
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
            return {'outcome':'blocked','reason':type(exc).__name__}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref',required=True); parser.add_argument('--patch',type=Path)
    parser.add_argument('--case',action='append',default=[]); parser.add_argument('--trials',type=int,default=3)
    parser.add_argument('--model',required=True); parser.add_argument('--effort',default='high',choices=['low','medium','high','xhigh'])
    parser.add_argument('--codex',default='codex'); parser.add_argument('--timeout',type=int,default=120)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.trials < 3 or args.timeout <= 0: parser.error('at least three trials and positive timeout required')
    try:
        if args.output.exists(): raise ValueError('output already exists')
        if not isolation_preflight(args.codex): raise ValueError('isolation preflight failed')
        corpus_bytes=CASES.read_bytes(); cases=yaml.safe_load(corpus_bytes)['cases']
        by_id={case['id']:case for case in cases}
        if len(by_id)!=len(cases): raise ValueError('duplicate case id')
        if args.case:
            missing=set(args.case)-set(by_id)
            if missing: raise ValueError('unknown cases: '+', '.join(sorted(missing)))
            cases=[by_id[x] for x in args.case]
        with tempfile.TemporaryDirectory(prefix='impact-source-') as tmp:
            source=Path(tmp); meta=snapshot(args.ref,args.patch,source)
            report={'scope':'synthetic source-file impact only', 'snapshot':meta,
                    'fixture_sha256':fixture_hash(), 'corpus_sha256':hashlib.sha256(corpus_bytes).hexdigest(),
                    'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    'shared_runner_sha256':hashlib.sha256((ROOT/'scripts/run_enhancement_benchmark.py').read_bytes()).hexdigest(),
                    'permission_profile_sha256':hashlib.sha256('\n'.join(PROFILE_OPTIONS).encode()).hexdigest(),
                    'environment_sha256':hashlib.sha256(json.dumps(benchmark_environment(),sort_keys=True).encode()).hexdigest(),
                    'host':platform.platform(), 'python':platform.python_version(),
                    'model':args.model,'effort':args.effort,'codex_version':codex_version(args.codex),
                    'results':[],'complete':False,
                    'limitations':['Static synthetic Python fixture; not a real repository or Java/Spring runtime.',
                                   'No private source, MCP, runtime execution, token or cost evidence.',
                                   'Ground truth is controlled fixture evidence, not independent human review.']}
            args.output.parent.mkdir(parents=True,exist_ok=True)
            for case in cases:
                for repeat in range(1,args.trials+1):
                    item=run_case(source,case,args.codex,args.model,args.effort,args.timeout)
                    item.update(case_id=case['id'],trial=repeat)
                    report['results'].append(item);write_report(args.output,report)
                    print('{} trial {} {}'.format(case['id'],repeat,item['outcome']),flush=True)
                    if len(report['results'])>=3 and all(x['outcome']=='blocked' for x in report['results'][-3:]): return 2
            report['complete']=True;write_report(args.output,report)
            return 0 if all(x['outcome']=='pass' for x in report['results']) else 1
    except (OSError,ValueError,KeyError,TypeError,yaml.YAMLError,subprocess.CalledProcessError) as exc:
        print('Evaluation setup failed: {}'.format(exc),file=sys.stderr);return 2


if __name__=='__main__': sys.exit(main())
