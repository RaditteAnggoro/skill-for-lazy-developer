"""Evaluate a local phase plan against recorded check results and current files."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.validate_phase_plan import validate_plan  # noqa: E402


def plan_digest(plan):
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def file_digest(root, name):
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("evidence paths must be relative POSIX paths")
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError("evidence path escapes its configured root")
    file = root
    for part in relative.parts:
        file = file / part
        if file.is_symlink():
            raise ValueError("evidence paths cannot contain symlinks")
    if not file.is_file():
        raise OSError("evidence file is missing or not regular")
    digest = hashlib.sha256()
    with file.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def declared_list(phase, key):
    values = phase.get(key)
    if (not isinstance(values, list) or not values
            or any(not isinstance(item, str) or not item.strip() for item in values)
            or len(set(values)) != len(values)):
        raise ValueError("{} requires unique nonempty {}".format(phase['id'], key))
    return values


def verify(plan, bundle, workspace, artifacts):
    """Derive phase status. Recorded observations do not authenticate their author."""
    errors = validate_plan(plan)
    if errors:
        raise ValueError("invalid plan: " + ", ".join(errors))
    if (not isinstance(bundle, dict) or type(bundle.get('version')) is not int
            or bundle['version'] != 1 or bundle.get('plan_sha256') != plan_digest(plan)
            or not isinstance(bundle.get('phases'), list)):
        raise ValueError("receipts must use version 1 and the current plan digest")
    for root in (workspace, artifacts):
        if not root.is_dir():
            raise ValueError("workspace and artifacts roots must be directories")
    phases = plan['phases']
    phase_ids = {phase['id'] for phase in phases}
    receipts = {}
    for item in bundle['phases']:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str):
            raise ValueError("invalid phase receipt")
        phase_id = item['id']
        if phase_id not in phase_ids or phase_id in receipts:
            raise ValueError("unknown or duplicate phase receipt")
        receipts[phase_id] = item

    trace = {}
    for phase in phases:
        phase_id = phase['id']
        inputs = declared_list(phase, 'inputs')
        checks = declared_list(phase, 'required_checks')
        unmet = [dep for dep in phase.get('depends_on', []) if trace[dep]['status'] != 'completed']
        if unmet:
            state = {'status': 'waiting', 'depends_on': unmet}
        elif phase_id not in receipts:
            state = {'status': 'ready', 'reason': 'no_receipt'}
        else:
            state = check_receipt(receipts[phase_id], inputs, checks, workspace, artifacts)
        trace[phase_id] = {'phase': phase_id, 'skill': phase['primary'], **state}
    return {'complete': all(row['status'] == 'completed' for row in trace.values()),
            'phases': list(trace.values())}


def check_receipt(receipt, inputs, checks, workspace, artifacts):
    recorded = receipt.get('input_sha256')
    observations = receipt.get('checks')
    if not isinstance(recorded, dict) or set(recorded) != set(inputs):
        raise ValueError("receipt must record exactly the declared inputs")
    if not isinstance(observations, dict) or set(observations) != set(checks):
        raise ValueError("receipt must record exactly the declared checks")
    for digest in recorded.values():
        if not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest):
            raise ValueError("invalid input digest")
    try:
        if any(file_digest(workspace, path) != recorded[path] for path in inputs):
            return {'status': 'stale', 'reason': 'input_changed'}
    except OSError:
        return {'status': 'stale', 'reason': 'input_unavailable'}
    for check_id in checks:
        observation = observations[check_id]
        if not isinstance(observation, dict) or observation.get('outcome') not in ('passed', 'failed', 'blocked', 'not_run'):
            raise ValueError("invalid check observation")
        if observation['outcome'] != 'passed':
            return {'status': 'blocked', 'check': check_id, 'reason': observation['outcome']}
        digest = observation.get('sha256')
        if not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest):
            raise ValueError("a passed check requires an artifact digest")
        try:
            if file_digest(artifacts, observation.get('path')) != digest:
                return {'status': 'stale', 'check': check_id, 'reason': 'artifact_changed'}
        except OSError:
            return {'status': 'blocked', 'check': check_id, 'reason': 'artifact_unavailable'}
    return {'status': 'completed', 'checks': checks}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('receipts', type=Path, nargs='?')
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    parser.add_argument('--artifacts', type=Path)
    parser.add_argument('--plan-digest', action='store_true')
    args = parser.parse_args(argv)
    try:
        plan = yaml.safe_load(args.plan.read_text(encoding='utf-8'))
        if args.plan_digest:
            errors = validate_plan(plan)
            if errors:
                raise ValueError("invalid plan: " + ", ".join(errors))
            print(plan_digest(plan))
            return 0
        if args.receipts is None or args.artifacts is None:
            parser.error('receipts and --artifacts are required for verification')
        bundle = json.loads(args.receipts.read_text(encoding='utf-8'))
        report = verify(plan, bundle, args.workspace, args.artifacts)
        print(json.dumps(report, indent=2))
        return 0 if report['complete'] else 1
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        print('Phase verification failed: {}'.format(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
