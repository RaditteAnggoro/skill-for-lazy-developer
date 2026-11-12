"""Compare read-only routing on isolated Git snapshots; this is not a task or UX benchmark."""

import argparse
import hashlib
import io
import json
import os
import platform
import re
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.run_routing_evals import build_command, evaluation_prompt, score_case, select_cases

FILESYSTEM_PROFILE = 'permissions.eval.filesystem={":root"="deny",":minimal"="read",":workspace_roots"="read"}'
PROFILE_OPTIONS = [
    '-c', 'default_permissions="eval"', '-c', FILESYSTEM_PROFILE,
    '-c', 'permissions.eval.network.enabled=false', '-c', 'web_search="disabled"',
    '-c', 'approval_policy="never"',
    '--disable', 'apps', '--disable', 'browser_use', '--disable', 'browser_use_external',
    '--disable', 'browser_use_full_cdp_access', '--disable', 'in_app_browser',
    '--disable', 'skill_mcp_dependency_install', '--disable', 'hooks',
    '--disable', 'plugins', '--disable', 'remote_plugin', '--disable', 'plugin_discovery_prefetch',
    '--enable', 'skip_host_skill_discovery',
]
SAFE_ENVIRONMENT_KEYS = ('PATH', 'HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL',
                         'LC_CTYPE', 'TMPDIR', 'TERM', 'SYSTEMROOT', 'WINDIR')


def benchmark_environment(source=None):
    """Pass only ordinary host settings; exclude provider keys and other secrets."""
    source = os.environ if source is None else source
    return {key: source[key] for key in SAFE_ENVIRONMENT_KEYS if key in source}


def write_report(path, report):
    """Replace an incomplete report atomically without exposing partial JSON."""
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix='.routing-ab-', delete=False) as stream:
        name = stream.name
        try:
            stream.write(json.dumps(report, indent=2) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            os.unlink(name)
            raise
    try:
        os.replace(name, path)
    except BaseException:
        os.unlink(name)
        raise


def snapshot(ref, patch, destination):
    """Extract tracked files from a fixed commit and apply an optional tracked patch."""
    commit = subprocess.run(['git', 'rev-parse', '--verify', ref + '^{commit}'], cwd=ROOT,
                            capture_output=True, text=True, check=True).stdout.strip()
    result = subprocess.run(['git', 'archive', '--format=tar', commit], cwd=ROOT,
                            capture_output=True, check=True)
    with tarfile.open(fileobj=io.BytesIO(result.stdout), mode='r:') as archive:
        for member in archive.getmembers():
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError('unsafe archive member: {}'.format(member.name))
        archive.extractall(destination)
    patch_hash = None
    if patch:
        patch = Path(patch).resolve(strict=True)
        patch_hash = hashlib.sha256(patch.read_bytes()).hexdigest()
        subprocess.run(['git', 'apply', '--check', '--', str(patch)], cwd=destination, check=True)
        subprocess.run(['git', 'apply', '--', str(patch)], cwd=destination, check=True)
    return {'commit': commit, 'patch_sha256': patch_hash}


def prepare_router_workspace(source, target):
    """Give the router the selected snapshot's instructions, not local private files."""
    if (source / 'AGENTS.md').is_symlink() or (source / '.agents/skills').is_symlink():
        raise ValueError('instructions must not be symlinks')
    for path in (source / '.agents/skills').rglob('*'):
        if path.is_symlink():
            raise ValueError('skill bundle contains a symlink')
    shutil.copytree(source / '.agents/skills', target / '.agents/skills')
    shutil.copy2(source / 'AGENTS.md', target / 'AGENTS.md')


def codex_version(executable):
    try:
        result = subprocess.run([executable, '--version'], capture_output=True, text=True,
                                env=benchmark_environment(),
                                timeout=10, check=False)
        return result.stdout.strip()[:200] if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def classify_failure(stderr):
    """Return only a coarse hint; never persist raw process diagnostics."""
    for label, pattern in (
        ('possible_rate_or_quota_limit', r'(?i)rate.?limit|usage.?limit|quota|\b429\b'),
        ('possible_authentication', r'(?i)unauthori[sz]ed|authentication failed|login required|\b401\b'),
        ('possible_network', r'(?i)connection (?:failed|refused)|network error|timed? out'),
        ('possible_sandbox', r'(?i)sandbox.*(?:failed|error|denied)|seatbelt.*(?:failed|error|denied)'),
    ):
        if re.search(pattern, stderr):
            return label
    return 'unclassified'


def isolation_preflight(codex):
    """Fail closed unless the active CLI denies an outside file, symlink and TCP."""
    nc = Path('/usr/bin/nc')
    if not nc.is_file() or not os.access(nc, os.X_OK):
        return False
    with tempfile.TemporaryDirectory(prefix='enhancement-isolation-') as tmp:
        root = Path(tmp)
        workspace = root / 'workspace'
        workspace.mkdir()
        inside = workspace / 'inside'
        outside = root / 'outside'
        inside.write_text('synthetic inside', encoding='utf-8')
        outside.write_text('synthetic outside', encoding='utf-8')
        (workspace / 'link').symlink_to(outside)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            port = str(listener.getsockname()[1])
            with socket.create_connection(('127.0.0.1', int(port)), timeout=2):
                connection, _ = listener.accept()
                connection.close()
            script = ('test -z "${LAZY_EVAL_SYNTHETIC_SECRET+x}" && '
                      '/bin/cat "$1" >/dev/null && ! /bin/cat "$2" >/dev/null 2>&1 '
                      '&& ! /bin/cat "$3" >/dev/null 2>&1 '
                      '&& { /usr/bin/nc -h >/dev/null 2>&1; test "$?" -lt 126; } '
                      '&& ! /usr/bin/nc -G 1 -z 127.0.0.1 "$4" >/dev/null 2>&1')
            command = ([codex, 'sandbox', '-P', 'eval'] + PROFILE_OPTIONS[2:6]
                       + ['-C', str(workspace), '--', '/bin/sh', '-c', script, 'probe',
                          str(inside), str(outside), str(workspace / 'link'), port])
            try:
                source = dict(os.environ, LAZY_EVAL_SYNTHETIC_SECRET='synthetic-canary')
                result = subprocess.run(command, capture_output=True, timeout=20, check=False,
                                        env=benchmark_environment(source))
                return result.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                return False


def trial(source, case, codex, model, timeout, schema, effort='high'):
    with tempfile.TemporaryDirectory(prefix='enhancement-route-') as tmp:
        workspace = Path(tmp)
        prepare_router_workspace(source, workspace)
        result = workspace / 'result.json'
        command = build_command(codex, workspace, result, model)
        sandbox = command.index('--sandbox')
        del command[sandbox:sandbox + 2]
        command.extend(PROFILE_OPTIONS)
        command.extend(['-c', 'model_reasoning_effort="{}"'.format(effort)])
        command[command.index('--output-schema') + 1] = str(schema)
        started = time.monotonic()
        try:
            completed = subprocess.run(command, input=evaluation_prompt(case), text=True,
                                       capture_output=True, timeout=timeout, check=False,
                                       env=benchmark_environment())
            wall_ms = round((time.monotonic() - started) * 1000)
            if completed.returncode:
                return {'outcome': 'blocked', 'errors': ['codex exited {}'.format(completed.returncode)],
                        'failure_hint': classify_failure(completed.stderr), 'wall_ms': wall_ms}
            actual = json.loads(result.read_text(encoding='utf-8'))
            differences = score_case(case, actual)
            return {'outcome': 'fail' if differences else 'pass', 'errors': differences,
                    'wall_ms': wall_ms, 'routing': {k: actual.get(k) for k in ('interaction', 'primary', 'supporting')}}
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            return {'outcome': 'blocked', 'errors': [type(exc).__name__],
                    'wall_ms': round((time.monotonic() - started) * 1000)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--candidate', help='Omit to record baseline trials before implementation')
    parser.add_argument('--baseline-patch', type=Path)
    parser.add_argument('--candidate-patch', type=Path)
    parser.add_argument('--corpus', type=Path, default=ROOT / 'tests/routing_cases.yaml')
    parser.add_argument('--case', action='append', default=[])
    parser.add_argument('--trials', type=int, default=3)
    parser.add_argument('--model', required=True, help='Explicit model used for both variants')
    parser.add_argument('--effort', choices=['low', 'medium', 'high', 'xhigh'], default='high')
    parser.add_argument('--codex', default='codex')
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true', help='Continue an incomplete run with identical settings')
    args = parser.parse_args(argv)
    if args.trials < 3 or args.timeout <= 0:
        parser.error('at least three trials and a positive timeout are required')
    if args.candidate_patch and not args.candidate:
        parser.error('--candidate-patch requires --candidate')
    try:
        if not isolation_preflight(args.codex):
            raise ValueError('sandbox isolation preflight failed; no model trials were run')
        corpus_bytes = args.corpus.read_bytes()
        cases = select_cases(yaml.safe_load(corpus_bytes)['cases'], args.case)
        if not cases:
            raise ValueError('empty corpus')
        with tempfile.TemporaryDirectory(prefix='enhancement-ab-') as tmp:
            root = Path(tmp)
            baseline = root / 'baseline'
            baseline.mkdir()
            metadata = {'baseline': snapshot(args.baseline, args.baseline_patch, baseline)}
            variants = [('baseline', baseline)]
            if args.candidate:
                candidate = root / 'candidate'
                candidate.mkdir()
                metadata['candidate'] = snapshot(args.candidate, args.candidate_patch, candidate)
                variants.append(('candidate', candidate))
            schema = root / 'routing.schema.json'
            shutil.copy2(ROOT / 'tests/routing_result.schema.json', schema)
            results = []
            args.output.mkdir(parents=True, exist_ok=True)
            json_path = args.output / 'routing-ab.json'
            markdown_path = args.output / 'routing-ab.md'
            report = {'scope': 'read-only routing only', 'model': args.model, 'effort': args.effort,
                      'host': platform.platform(), 'python': platform.python_version(),
                      'codex_version': codex_version(args.codex), 'network_availability': None,
                      'environment_sha256': hashlib.sha256(json.dumps(benchmark_environment(),
                          sort_keys=True).encode()).hexdigest(),
                      'isolation_preflight': 'pass',
                      'permission_profile_sha256': hashlib.sha256('\n'.join(PROFILE_OPTIONS).encode()).hexdigest(),
                      'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      'scorer_sha256': hashlib.sha256((ROOT / 'scripts/run_routing_evals.py').read_bytes()).hexdigest(),
                      'corpus_sha256': hashlib.sha256(corpus_bytes).hexdigest(),
                      'schema_sha256': hashlib.sha256(schema.read_bytes()).hexdigest(),
                      'snapshots': metadata, 'trials': args.trials,
                      'case_ids': [case['id'] for case in cases], 'results': results,
                      'complete': False,
                      'limitations': ['Token/cost metrics and network availability not collected.',
                                      'Routing classification does not execute tasks or measure UI quality.',
                                      'Model response text and full tool logs are not retained; wording failures need independent review.',
                                      'The synthetic preflight covers local shell access, not every possible external tool or connector.']}
            if args.resume:
                if not json_path.is_file() or markdown_path.exists():
                    raise ValueError('resume needs an incomplete routing-ab.json')
                previous = json.loads(json_path.read_text(encoding='utf-8'))
                if previous.get('complete'):
                    raise ValueError('completed benchmark cannot be resumed')
                for key in ('scope', 'model', 'effort', 'host', 'python', 'codex_version', 'network_availability', 'environment_sha256',
                            'isolation_preflight', 'permission_profile_sha256',
                            'runner_sha256', 'scorer_sha256', 'corpus_sha256',
                            'schema_sha256', 'snapshots', 'trials', 'case_ids'):
                    if previous.get(key) != report[key]:
                        raise ValueError('resume configuration differs: {}'.format(key))
                results.extend(previous['results'])
            elif json_path.exists() or markdown_path.exists():
                raise ValueError('output already exists; choose a fresh directory')
            allowed = {(case['id'], variant, repeat) for case in cases for variant, _ in variants
                       for repeat in range(1, args.trials + 1)}
            done = {(item['case_id'], item['variant'], item['trial']) for item in results}
            if len(done) != len(results) or not done <= allowed:
                raise ValueError('resume report has duplicate or unexpected trials')
            for case in cases:
                for repeat in range(1, args.trials + 1):
                    for variant, source in variants:
                        if (case['id'], variant, repeat) in done:
                            continue
                        item = trial(source, case, args.codex, args.model, args.timeout, schema, args.effort)
                        item.update(case_id=case['id'], variant=variant, trial=repeat)
                        results.append(item)
                        write_report(json_path, report)
                        print('{} {} {} {}'.format(case['id'], variant, repeat, item['outcome']), flush=True)
                        if len(results) >= 3 and all(x['outcome'] == 'blocked' for x in results[-3:]):
                            print('Three consecutive blocked trials; run left incomplete.', file=sys.stderr)
                            return 2
            report['complete'] = True
            write_report(json_path, report)
            counts = {v: {s: sum(x['outcome'] == s and x['variant'] == v for x in results)
                          for s in ('pass', 'fail', 'blocked')} for v in metadata}
            markdown_path.write_text('# Routing A/B\n\nScope: read-only routing; no task execution.\n\n'
                + '\n'.join('- {}: {}'.format(v, counts[v]) for v in counts) + '\n', encoding='utf-8')
            return 1 if any(x['outcome'] != 'pass' for x in results) else 0
    except (OSError, ValueError, KeyError, yaml.YAMLError, subprocess.CalledProcessError) as exc:
        print('Benchmark setup failed: {}'.format(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
