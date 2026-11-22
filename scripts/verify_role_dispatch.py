"""Exercise a Codex custom role in an isolated, read-only synthetic workspace."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from queue import Empty, Queue
import subprocess
import sys
import tempfile
from threading import Thread
import time
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.run_enhancement_benchmark import (  # noqa: E402
    PROFILE_OPTIONS, benchmark_environment, codex_version, isolation_preflight,
)

ROLE = 'ld-codebase-explorer'
PROMPT = (f'Use the host spawn_agent tool exactly once with agent_type {ROLE}. This is an authorized synthetic canary. '
          'Ask the child to find the callsite in approve and the target declaration in bridge.py. '
          'Ask it to include its synthetic role marker. Use the host wait tool until the child completes, '
          'then relay the exact caller and target anchors. If a wait returns pending, keep waiting within the budget. '
          'If the role or dispatch is unavailable, return DISPATCH_UNAVAILABLE. Do not do the analysis yourself.')


def assess(events, parent, marker):
    activity = {'started': set(), 'completed': set()}
    matching_children = set()
    parent_handoff = False
    for event in events:
        if event.get('method') != 'item/completed':
            continue
        payload = event.get('params', {})
        item = payload.get('item', {})
        thread = payload.get('threadId')
        if thread == parent and item.get('type') == 'subAgentActivity':
            kind, child = item.get('kind'), item.get('agentThreadId')
            if kind in activity and isinstance(child, str) and child and child != parent:
                activity[kind].add(child)
        if item.get('type') == 'agentMessage' and item.get('phase') == 'final_answer':
            body = item.get('text', '')
            if isinstance(body, str) and all(token in body for token in ('sample.py:4', 'bridge.py:1', 'convert')):
                if thread == parent:
                    parent_handoff = (len(activity['started']) == 1 and activity['started'] == activity['completed']
                                      and activity['started'] <= matching_children)
                elif marker in body:
                    matching_children.add(thread)
    child_ids = activity['started']
    return {'dispatch_observed': len(child_ids) == 1,
            'child_completed': len(child_ids) == 1 and activity['completed'] == child_ids,
            'child_evidence_matches': len(child_ids) == 1 and child_ids <= matching_children,
            'parent_handoff_matches': parent_handoff}


def digest_workspace(workspace):
    return {path.relative_to(workspace).as_posix(): ('symlink' if path.is_symlink()
                                                   else hashlib.sha256(path.read_bytes()).hexdigest())
            for path in workspace.rglob('*') if path.is_symlink() or path.is_file()}


def write_denied(codex, work, env):
    target = work / 'write-canary.txt'
    command = [codex, 'sandbox', '-P', 'eval', *PROFILE_OPTIONS[2:6], '-C', str(work), '--',
               '/bin/sh', '-c', '/bin/cat sample.py >/dev/null && ! /usr/bin/touch "$1" 2>/dev/null',
               'probe', str(target)]
    result = subprocess.run(command, env=env, capture_output=True, timeout=15, check=False)
    return result.returncode == 0 and not target.exists()


def observe(codex, fixture, env, model, timeout, events):
    args = [codex, 'app-server', '--stdio', *PROFILE_OPTIONS, '--enable', 'multi_agent',
            '--disable', 'multi_agent_v2', '-c', 'agents.max_depth=1']
    server = subprocess.Popen(args, cwd=fixture, env=env, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    inbox = Queue()

    def read_events():
        for line in server.stdout:
            try:
                inbox.put(json.loads(line))
            except ValueError:
                continue
        inbox.put(None)

    def send(method, params, request=None):
        event = {'method': method, 'params': params}
        if request is not None:
            event['id'] = request
        server.stdin.write(json.dumps(event) + '\n')
        server.stdin.flush()

    Thread(target=read_events, daemon=True).start()
    deadline = time.monotonic() + timeout
    parent = None
    try:
        send('initialize', {'clientInfo': {'name': 'lazy-developer-canary', 'version': '1'},
                            'capabilities': {'experimentalApi': True}}, 1)
        while True:
            event = inbox.get(timeout=max(0, deadline - time.monotonic()))
            if event is None or not isinstance(event, dict) or 'error' in event:
                return parent, 'host_error'
            events.append(event)
            if event.get('id') == 1:
                send('initialized', {})
                # The host restores the parent's rollout during spawn. It lives entirely in the temporary home.
                send('thread/start', {'cwd': str(fixture), 'model': model, 'ephemeral': False}, 2)
            elif event.get('id') == 2:
                result = event['result']
                sandbox = result.get('sandbox', {})
                if (sandbox.get('type') != 'readOnly' or sandbox.get('networkAccess') is not False
                        or result.get('approvalPolicy') != 'never'
                        or (result.get('activePermissionProfile') or {}).get('id') != 'eval'):
                    return None, 'permission_restricted'
                parent = result['thread']['id']
                send('turn/start', {'threadId': parent, 'input': [{'type': 'text', 'text': PROMPT}], 'effort': 'low'}, 3)
            elif event.get('method') == 'turn/completed' and event.get('params', {}).get('threadId') == parent:
                status = event['params'].get('turn', {}).get('status')
                return parent, None if status == 'completed' else 'host_error'
            if time.monotonic() >= deadline:
                return parent, 'agent_timeout_or_budget'
    except Empty:
        return parent, 'agent_timeout_or_budget'
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
        server.stdin.close()
        server.stdout.close()


def verify(codex, model, timeout):
    report = {'host': codex_version(codex), 'model': model, 'role': ROLE, 'status': 'blocked',
              'execution_mode': 'single-agent-role-guided'}
    if not isolation_preflight(codex):
        return {**report, 'reason': 'permission_restricted'}
    configured_home = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex'))
    auth = configured_home / 'auth.json'
    if not auth.is_file():
        return {**report, 'reason': 'auth_required'}
    with tempfile.TemporaryDirectory(prefix='ld-dispatch-') as temporary:
        root = Path(temporary).resolve()
        home, fixture = root / 'home', root / 'fixture'
        home.mkdir()
        (home / 'auth.json').symlink_to(auth.resolve())
        (home / 'config.toml').write_text(f'[projects.{json.dumps(str(fixture))}]\ntrust_level = "trusted"\n'
                                          '\n[agents]\nenabled = true\nmax_concurrent_threads_per_session = 1\n',
                                          encoding='utf-8')
        agents = fixture / '.codex/agents'
        agents.mkdir(parents=True)
        git_env = dict(benchmark_environment(), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        subprocess.run(['git', 'init', '--template=', '-q', str(fixture)], env=git_env, check=True, timeout=10)
        marker = f'LD-ROLE-{uuid4().hex}'
        wrapper = (ROOT / '.codex/agents' / f'{ROLE}.toml').read_text(encoding='utf-8')
        wrapper = wrapper.replace('Return sections:', f'Include role marker {marker} in your evidence. Return sections:', 1)
        (agents / f'{ROLE}.toml').write_text(wrapper, encoding='utf-8')
        (fixture / 'sample.py').write_text('from bridge import convert\n\ndef approve(value):\n    return convert(value)\n')
        (fixture / 'bridge.py').write_text('def convert(value):\n    return int(value)\n')
        env = dict(benchmark_environment(), CODEX_HOME=str(home))
        if not write_denied(codex, fixture, env):
            return {**report, 'reason': 'permission_restricted'}
        before = digest_workspace(fixture)
        events = []
        try:
            parent, reason = observe(codex, fixture, env, model, timeout, events)
        except (BrokenPipeError, KeyError, TypeError):
            parent, reason = None, 'host_error'
        checks = {**assess(events, parent, marker), 'workspace_unchanged': before == digest_workspace(fixture)}
        if reason is None and all(checks.values()):
            return {**report, 'status': 'pass', 'execution_mode': 'subagent', 'checks': checks}
        return {**report, 'reason': reason or 'verified_child_evidence_missing', 'checks': checks}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex', default='codex')
    parser.add_argument('--model', required=True)
    parser.add_argument('--timeout', type=float, default=90)
    args = parser.parse_args(argv)
    if not 0 < args.timeout <= 300:
        parser.error('timeout must be greater than zero and at most 300 seconds')
    try:
        report = verify(args.codex, args.model, args.timeout)
    except (OSError, subprocess.SubprocessError):
        report = {'status': 'blocked', 'reason': 'host_error', 'execution_mode': 'single-agent-role-guided'}
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'pass' else 3


if __name__ == '__main__':
    sys.exit(main())
