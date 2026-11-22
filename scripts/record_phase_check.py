"""Record a phase check from an explicitly supplied local command."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.run_enhancement_benchmark import write_report  # noqa: E402
from scripts.verify_phase_receipts import file_digest, plan_digest, verify  # noqa: E402


def record(plan, bundle, phase_id, check_id, workspace, artifacts, command, timeout):
    report = verify(plan, bundle, workspace, artifacts)
    state = next((row for row in report['phases'] if row['phase'] == phase_id), None)
    if state is None or state['status'] == 'waiting':
        raise ValueError('phase is unknown or its dependencies are incomplete')
    phase = next(row for row in plan['phases'] if row['id'] == phase_id)
    if check_id not in phase['required_checks']:
        raise ValueError('check is not declared in the phase')
    inputs = {name: file_digest(workspace, name) for name in phase['inputs']}
    exit_code = None
    try:
        exit_code = subprocess.run(command, cwd=workspace, timeout=timeout, check=False).returncode
        outcome = 'passed' if exit_code == 0 else 'failed'
    except (OSError, subprocess.TimeoutExpired):
        outcome = 'blocked'
    try:
        unchanged = all(file_digest(workspace, name) == value for name, value in inputs.items())
    except (OSError, ValueError):
        unchanged = False
    if not unchanged:
        outcome = 'blocked'
    run_id = uuid4().hex
    filename = f'phase-check-{run_id}.json'
    # Capture execution provenance without storing raw argv, stdout, environment, or credentials.
    write_report(artifacts / filename, {
        'run_id': run_id, 'plan_sha256': bundle['plan_sha256'], 'phase': phase_id, 'check': check_id,
        'argv_sha256': hashlib.sha256(json.dumps(command).encode()).hexdigest(),
        'input_sha256': inputs, 'inputs_unchanged': unchanged, 'exit_code': exit_code, 'outcome': outcome,
    })
    receipt = next((row for row in bundle['phases'] if row['id'] == phase_id), None)
    if receipt is None:
        receipt = {'id': phase_id, 'input_sha256': inputs, 'checks': {}}
        bundle['phases'].append(receipt)
    if receipt['input_sha256'] != inputs:
        receipt.update(input_sha256=inputs, checks={})
    for name in phase['required_checks']:
        receipt['checks'].setdefault(name, {'outcome': 'not_run'})
    receipt['checks'][check_id] = {
        'outcome': outcome, 'path': filename, 'sha256': file_digest(artifacts, filename),
        'run_id': run_id,
    }
    return outcome


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('receipts', type=Path)
    parser.add_argument('--phase', required=True)
    parser.add_argument('--check', required=True)
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=120)
    split = argv.index('--') if '--' in argv else len(argv)
    args = parser.parse_args(argv[:split])
    command = argv[split+1:]
    if not command or args.timeout <= 0:
        parser.error('provide an explicit COMMAND after -- and a positive timeout')
    try:
        plan = yaml.safe_load(args.plan.read_text(encoding='utf-8'))
        if args.receipts.exists():
            bundle = json.loads(args.receipts.read_text(encoding='utf-8'))
        else:
            bundle = {'version': 1, 'plan_sha256': plan_digest(plan), 'phases': []}
        args.artifacts.mkdir(parents=True, exist_ok=True)
        args.receipts.parent.mkdir(parents=True, exist_ok=True)
        outcome = record(plan, bundle, args.phase, args.check, args.workspace, args.artifacts,
                         command, args.timeout)
        write_report(args.receipts, bundle)
        print(f'{args.phase}/{args.check}: {outcome}')
        return 0 if outcome == 'passed' else 1
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        print(f'Could not record phase check: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
