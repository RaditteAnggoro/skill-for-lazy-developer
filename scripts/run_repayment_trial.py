"""Run a synthetic repayment repair trial in a restricted temporary workspace.

This is one SQLite fixture, not a production banking or Java benchmark. Never run
model-generated code outside the sandbox; no provider logs or database records are saved.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.run_enhancement_benchmark import (  # noqa: E402
    PROFILE_OPTIONS, benchmark_environment, classify_failure, codex_version,
    prepare_router_workspace, snapshot, write_report,
)

FIXTURE = ROOT / 'tests/enhancement/fixtures/repayment'
SYSTEM_PYTHON = Path(sys.executable).resolve()
TASK_FILESYSTEM = ('permissions.eval.filesystem={":root"="deny",":minimal"="read",'
                   '"/Library/Developer/CommandLineTools"="read",'
                   '":workspace_roots"={"."="write",".agents"="read",'
                   '"AGENTS.md"="read","README.md"="read","verify.py"="read"}}')


def task_options():
    return [TASK_FILESYSTEM if value.startswith('permissions.eval.filesystem=') else value
            for value in PROFILE_OPTIONS]


def sandbox_command(codex, workspace, command):
    options = task_options()
    return ([codex, 'sandbox', '-P', 'eval'] + options[2:6]
            + ['-C', str(workspace), '--'] + command)


def preflight(codex):
    """Prove only selected local OS boundaries using synthetic data; fail closed."""
    if not SYSTEM_PYTHON.is_relative_to(Path('/Library/Developer/CommandLineTools')):
        return False
    if not os.path.isfile('/usr/bin/nc') or not os.access('/usr/bin/nc', os.X_OK):
        return False
    with tempfile.TemporaryDirectory(prefix='repayment-preflight-') as tmp:
        root = Path(tmp); workspace = root / 'work'; workspace.mkdir()
        (workspace / '.agents').mkdir()
        (workspace / '.agents/rule').write_text('protected')
        for name in ('README.md', 'AGENTS.md', 'verify.py', 'ledger.py'):
            (workspace / name).write_text('synthetic')
        outside = root / 'outside'; outside.write_text('synthetic outside')
        (workspace / 'link').symlink_to(outside)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); listener.listen(1)
            port = str(listener.getsockname()[1])
            with socket.create_connection(('127.0.0.1', int(port)), timeout=2):
                connection, _ = listener.accept(); connection.close()
            command = ('test -z "${LAZY_EVAL_SYNTHETIC_SECRET+x}" '
                       '&& /bin/cat "$1" >/dev/null && printf changed > "$1" '
                       '&& ! printf changed > "$2" 2>/dev/null '
                       '&& ! printf changed > "$3" 2>/dev/null '
                       '&& ! printf changed > "$4" 2>/dev/null '
                       '&& ! /bin/cat "$4" >/dev/null 2>&1 '
                       '&& ! /bin/cat "$5" >/dev/null 2>&1 '
                       '&& { /usr/bin/nc -h >/dev/null 2>&1; test "$?" -lt 126; } '
                       '&& ! /usr/bin/nc -G 1 -z 127.0.0.1 "$6" >/dev/null 2>&1')
            args = ['/bin/sh', '-c', command, 'probe', str(workspace/'ledger.py'),
                    str(workspace/'verify.py'), str(workspace/'.agents/rule'), str(outside),
                    str(workspace/'link'), port]
            env = benchmark_environment(dict(os.environ, LAZY_EVAL_SYNTHETIC_SECRET='synthetic'))
            try:
                result = subprocess.run(sandbox_command(codex, workspace, args), env=env,
                                        capture_output=True, timeout=20, check=False)
                return (result.returncode == 0 and (workspace/'ledger.py').read_text() == 'changed'
                        and (workspace/'verify.py').read_text() == 'synthetic'
                        and (workspace/'.agents/rule').read_text() == 'protected'
                        and outside.read_text() == 'synthetic outside')
            except (OSError, subprocess.TimeoutExpired):
                return False


def fixture_digest():
    digest = hashlib.sha256()
    for name in ('README.md', 'ledger.py', 'verify.py'):
        content = (FIXTURE / name).read_bytes()
        digest.update(name.encode() + b'\0' + len(content).to_bytes(8, 'big') + content)
    return digest.hexdigest()


def grade_copy(codex, grade):
    """Run the trusted verifier in the same local sandbox, reporting no raw output."""
    command = [str(SYSTEM_PYTHON), '-I', '-B', '-c',
               'import runpy,sys; root,script=sys.argv[1:]; sys.argv=[script]; sys.path.insert(0,root); runpy.run_path(script,run_name="__main__")',
               str(grade), str(grade/'verify.py')]
    env = benchmark_environment()
    env['LAZY_FIXTURE_TMPDIR'] = str(grade)
    try:
        result = subprocess.run(sandbox_command(codex, grade, command), capture_output=True,
                                env=env, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return 'blocked', 'grader could not run'
    output = result.stderr.decode('utf-8', errors='replace')
    if 'Ran 3 tests' not in output:
        return 'blocked', 'verifier did not complete its three checks'
    if result.returncode == 0 and '\nOK' in output:
        return 'pass', 'synthetic verifier passed'
    if result.returncode != 0 and 'FAILED (' in output:
        return 'fail', 'synthetic verifier failed'
    return 'blocked', 'grader returned an inconsistent result'


def run_one(source, codex, model, effort, timeout):
    with tempfile.TemporaryDirectory(prefix='repayment-model-') as tmp:
        root = Path(tmp); workspace = root/'work'; workspace.mkdir()
        prepare_router_workspace(source, workspace)
        for name in ('README.md', 'ledger.py', 'verify.py'):
            shutil.copy2(FIXTURE/name, workspace/name)
        protected = {name: hashlib.sha256((workspace/name).read_bytes()).hexdigest()
                     for name in ('README.md', 'verify.py', 'AGENTS.md')}
        result_path = root/'result.txt'
        prompt = ('A repayment can be posted twice when processing restarts after a commit. '
                  'Find the cause and fix it safely. Keep both ledger sides balanced. '
                  'This is a synthetic SQLite fixture. Change only ledger.py; preserve '
                  'README.md, verify.py and agent instructions. Run python3 verify.py.')
        command = ([codex, 'exec', '--ephemeral', '--ignore-user-config', '--skip-git-repo-check']
                   + task_options() + ['--output-last-message', str(result_path), '--json',
                                      '--cd', str(workspace), '--model', model,
                                      '-c', 'model_reasoning_effort="{}"'.format(effort)])
        start = time.monotonic()
        model_env = benchmark_environment()
        model_env['LAZY_FIXTURE_TMPDIR'] = str(workspace)
        try:
            completed = subprocess.run(command, input=prompt, text=True, capture_output=True,
                                       timeout=timeout, env=model_env, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {'outcome': 'blocked', 'reason': type(exc).__name__,
                    'wall_ms': round((time.monotonic()-start)*1000)}
        wall_ms = round((time.monotonic()-start)*1000)
        if completed.returncode:
            return {'outcome': 'blocked', 'reason': classify_failure(completed.stderr), 'wall_ms': wall_ms}
        for name, digest in protected.items():
            path = workspace/name
            if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                return {'outcome': 'fail', 'reason': 'protected file changed', 'wall_ms': wall_ms}
        for path in workspace.rglob('*'):
            relative = path.relative_to(workspace)
            if relative.parts[0] == '.agents':
                continue
            if path.is_symlink():
                return {'outcome': 'fail', 'reason': 'unexpected symlink', 'wall_ms': wall_ms}
            if path.is_file() and relative.as_posix() not in ('README.md', 'verify.py', 'AGENTS.md', 'ledger.py'):
                if not ('__pycache__' in relative.parts and path.suffix == '.pyc'):
                    return {'outcome': 'fail', 'reason': 'unexpected file created', 'wall_ms': wall_ms}
        code = workspace/'ledger.py'
        if code.is_symlink() or not code.is_file() or code.stat().st_size > 131072:
            return {'outcome': 'fail', 'reason': 'invalid target file', 'wall_ms': wall_ms}
        # Grade a clean copy: discard model-created files and bytecode, and use the
        # original verifier. The verifier and candidate code still run inside Seatbelt.
        grade = root/'grade'; grade.mkdir()
        shutil.copy2(FIXTURE/'verify.py', grade/'verify.py')
        shutil.copy2(code, grade/'ledger.py')
        outcome, reason = grade_copy(codex, grade)
        return {'outcome': outcome, 'reason': reason, 'wall_ms': wall_ms}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ref', required=True); p.add_argument('--patch', type=Path)
    p.add_argument('--variant', choices=['baseline', 'candidate'], required=True)
    p.add_argument('--model', required=True); p.add_argument('--effort', default='high', choices=['low','medium','high','xhigh'])
    p.add_argument('--codex', default='codex'); p.add_argument('--timeout', type=int, default=300)
    p.add_argument('--trials', type=int, default=3); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(argv)
    if args.trials < 3 or args.timeout <= 0:
        p.error('at least three trials and a positive timeout are required')
    try:
        if args.output.exists(): raise ValueError('output already exists')
        if not preflight(args.codex): raise ValueError('task sandbox preflight failed; no model trials run')
        with tempfile.TemporaryDirectory(prefix='repayment-source-') as tmp:
            source = Path(tmp); meta = snapshot(args.ref, args.patch, source)
            report = {'scope': 'one synthetic SQLite repayment fixture', 'variant': args.variant,
                      'snapshot': meta, 'fixture_sha256': fixture_digest(), 'model': args.model,
                      'effort': args.effort, 'codex_version': codex_version(args.codex),
                      'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      'shared_runner_sha256': hashlib.sha256((ROOT/'scripts/run_enhancement_benchmark.py').read_bytes()).hexdigest(),
                      'permission_profile_sha256': hashlib.sha256('\n'.join(task_options()).encode()).hexdigest(),
                      'environment_sha256': hashlib.sha256(json.dumps(benchmark_environment(),sort_keys=True).encode()).hexdigest(),
                      'complete': False, 'results': [],
                      'limitations': ['Synthetic SQLite only; no production, Java, external settlement, or real bank safety claim.',
                                      'Raw model output and provider token/cost metrics are not retained.',
                                      'The verifier is not an adversarial security boundary against intentionally malicious fixture code.',
                                      'Preflight covers synthetic local boundaries, not all host surfaces.']}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            for i in range(1, args.trials+1):
                result = run_one(source, args.codex, args.model, args.effort, args.timeout)
                result['trial'] = i; report['results'].append(result); write_report(args.output, report)
                print('{} trial {} {}'.format(args.variant, i, result['outcome']), flush=True)
                if len(report['results']) >= 3 and all(x['outcome']=='blocked' for x in report['results'][-3:]):
                    return 2
            report['complete'] = True; write_report(args.output, report)
            return 0 if all(x['outcome']=='pass' for x in report['results']) else 1
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print('Trial setup failed: {}'.format(exc), file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())
