"""Check transaction cases for idempotency, approval, retry bounds, and recovery."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.analyze_financial_source import analyze  # noqa: E402


REQUIRED_KINDS = {"money", "ledger", "batch", "reconciliation"}


def check(data):
    errors = []
    if not isinstance(data, dict) or not isinstance(data.get("operations"), list) or not data["operations"]:
        return ["operations must be a nonempty list"]
    for index, operation in enumerate(data["operations"]):
        prefix = "operation {}".format(index)
        if not isinstance(operation, dict):
            errors.append(prefix + " must be a mapping")
            continue
        for key in ("id", "kind", "idempotency", "approval", "retry", "recovery"):
            if key not in operation:
                errors.append(prefix + " missing " + key)
        kind = operation.get("kind")
        if kind not in REQUIRED_KINDS:
            errors.append(prefix + " has unsupported kind: {}".format(kind))
            continue
        if operation.get("idempotency") is not True and not operation.get("idempotency_key"):
            errors.append(prefix + " needs an idempotency key or true")
        if operation.get("approval") is not True:
            errors.append(prefix + " needs explicit approval for its impact")
        retry = operation.get("retry")
        if retry not in ("bounded", "none", "bounded_with_backoff"):
            errors.append(prefix + " retry must be bounded or none")
        recovery = operation.get("recovery")
        if not isinstance(recovery, str) or not recovery.strip():
            errors.append(prefix + " needs a recovery/compensation description")
    return errors


def load(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, nargs="?")
    parser.add_argument("--source", type=Path, action="append", default=[])
    parser.add_argument("--reviewed", type=Path, help="JSON dispositions for source findings")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if bool(args.path) == bool(args.source) or (args.reviewed and not args.source):
        parser.error('choose one YAML declaration or explicit --source paths')
    if args.source:
        try:
            findings = analyze(args.source, reviewed=args.reviewed)
        except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
            print(f'Source check blocked: {exc}', file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps({'mode': 'source_review', 'findings': findings}, indent=2))
        else:
            for finding in findings:
                print('{classification} {rule} {file}:{line} {method} — {reason} {verification}'.format(**finding))
            print(f'{len(findings)} source finding(s). Verify financial outcomes separately.')
        return 0
    try:
        errors = check(load(args.path))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        print("transaction check failed: {}".format(exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"safe": not errors, "errors": errors}, indent=2, ensure_ascii=False))
    elif errors:
        for error in errors:
            print("FAIL " + error)
    else:
        print("Transaction cases pass.")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
