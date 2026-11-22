"""Validate or stage a skill-learning proposal without modifying active skills."""

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.verify_phase_receipts import file_digest  # noqa: E402

SKILLS = ROOT / ".agents/skills"
REQUIRED = {
    "proposal_id", "status", "owner_skill", "reference_target", "trigger",
    "suggested_rule", "why", "evidence", "constraints", "privacy_review",
    "security_review", "baseline_eval", "candidate_eval", "approval",
}
SENSITIVE = re.compile(r"(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|password\s*[:=]\s*\S+|api[_-]?key\s*[:=]\s*\S+)", re.I)
INJECTION = re.compile(r"(ignore (all|previous) instructions|disable (the )?(safety|approval)|system prompt|curl\s+[^\n|]+\|\s*(ba)?sh)", re.I)
PII = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")


def load(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def validate(data):
    errors = []
    if not isinstance(data, dict):
        return ["proposal must be a mapping"]
    unknown = sorted(set(data) - REQUIRED)
    missing = sorted(REQUIRED - set(data))
    if unknown:
        errors.append("unknown fields: " + ", ".join(unknown))
    if missing:
        errors.append("missing fields: " + ", ".join(missing))
    if not isinstance(data.get("proposal_id"), str) or not re.fullmatch(r"skill-lesson-\d{8}-\d{3}", data.get("proposal_id", "")):
        errors.append("invalid proposal_id")
    if data.get("status") != "candidate":
        errors.append("status must be candidate")
    owner = data.get("owner_skill")
    if (not isinstance(owner, str) or not re.fullmatch(r'[a-z0-9-]+', owner)
            or not (SKILLS / owner / "SKILL.md").is_file()):
        errors.append("owner_skill is not an installed skill")
    reference = data.get("reference_target")
    if (not isinstance(reference, str) or not reference.startswith(".agents/skills/{}/".format(owner))
            or ".." in PurePosixPath(reference).parts or "\\" in reference):
        errors.append("reference_target must remain inside the owner skill")
    if not isinstance(data.get("trigger"), str) or len(data["trigger"].strip()) < 3:
        errors.append("trigger is required")
    if not isinstance(data.get("suggested_rule"), str) or len(data["suggested_rule"].strip()) < 10:
        errors.append("suggested_rule is required")
    if not isinstance(data.get("why"), str) or len(data["why"].strip()) < 10:
        errors.append("why is required")
    evidence = data.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence must be a nonempty list")
    else:
        for item in evidence:
            if not isinstance(item, dict) or set(item) - {'receipts'} != {"type", "case_id", "result"}:
                errors.append("evidence items need type, case_id, result")
                continue
            if item["result"] not in ("observed_fail_then_pass", "observed_pass", "observed_fail", "not_observed"):
                errors.append("invalid evidence result")
            if item["result"] == "not_observed":
                errors.append("unobserved evidence cannot justify promotion")
    for key in ("constraints",):
        if not isinstance(data.get(key), list) or not data[key] or not all(isinstance(item, str) and item for item in data[key]):
            errors.append(key + " must be a nonempty string list")
    for key in ("privacy_review", "security_review", "baseline_eval", "candidate_eval", "approval"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(key + " must be recorded")
    return errors


def verify_evidence(data, artifacts):
    """Check immutable run references without granting approval or promotion."""
    expectations = {'observed_fail_then_pass': ('failed', 'passed'),
                    'observed_pass': ('passed',), 'observed_fail': ('failed',)}
    seen = set()
    for item in data['evidence']:
        required = expectations[item['result']]
        references = item.get('receipts')
        if not isinstance(references, list) or len(references) != len(required):
            raise ValueError('proposal needs one reference for each claimed observation')
        commands = set()
        for ref, outcome in zip(references, required):
            if not isinstance(ref, dict) or set(ref) != {'run_id', 'sha256'}:
                raise ValueError('invalid evidence reference')
            run_id = ref['run_id']
            if not isinstance(run_id, str) or not re.fullmatch('[a-f0-9]{32}', run_id) or run_id in seen:
                raise ValueError('invalid or reused run ID')
            seen.add(run_id)
            filename = f'phase-check-{run_id}.json'
            if file_digest(artifacts, filename) != ref['sha256']:
                raise ValueError('evidence digest mismatch')
            with (artifacts / filename).open('rb') as stream:
                observation = json.loads(stream.read(65537))
            if not isinstance(observation, dict):
                raise ValueError('invalid evidence record')
            exit_code, fingerprint = observation.get('exit_code'), observation.get('argv_sha256')
            if (observation.get('run_id') != run_id or observation.get('check') != item['case_id']
                    or observation.get('outcome') != outcome or observation.get('inputs_unchanged') is not True
                    or type(exit_code) is not int or (exit_code == 0) != (outcome == 'passed')
                    or not isinstance(fingerprint, str) or not re.fullmatch('[a-f0-9]{64}', fingerprint)):
                raise ValueError('recorded check does not support the proposal evidence')
            commands.add(fingerprint)
        if len(commands) != 1:
            raise ValueError('before and after must run the same check command')


def content_error(data):
    text = json.dumps(data, ensure_ascii=False)
    if SENSITIVE.search(text):
        return "sensitive secret or credential material"
    if PII.search(text):
        return "email or PII"
    if INJECTION.search(text):
        return "prompt-injection or unsafe command content"
    return None


def duplicate(data):
    rule = " ".join(data["suggested_rule"].casefold().split())
    for path in sorted(SKILLS.rglob("*.md")):
        try:
            body = " ".join(path.read_text(encoding="utf-8", errors="replace").casefold().split())
            if rule and rule in body:
                return str(path)
        except OSError:
            continue
    return None


def stage(data, output_dir):
    proposal_id = data.get('proposal_id')
    if not isinstance(proposal_id, str) or not re.fullmatch(r'skill-lesson-\d{8}-\d{3}', proposal_id):
        raise ValueError('invalid proposal_id')
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / (proposal_id + ".yaml")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output_dir, mode='w', encoding='utf-8', delete=False) as stream:
            temporary = Path(stream.name)
            yaml.safe_dump(data, stream, sort_keys=False, allow_unicode=True)
        os.link(temporary, path)  # Publish without overwriting a previously reviewed proposal.
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "propose", "verify-evidence"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--input", type=Path, required=True)
        if name == "propose":
            cmd.add_argument("--output-dir", type=Path, default=ROOT / ".agents/artifacts/skill-proposals")
        elif name == 'verify-evidence':
            cmd.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        data = load(args.input)
    except (OSError, yaml.YAMLError) as exc:
        print("proposal failed: {}".format(exc), file=sys.stderr)
        return 2
    errors = validate(data)
    problem = content_error(data) if not errors else None
    duplicate_path = duplicate(data) if not errors and not problem else None
    if problem:
        errors.append(problem)
    if duplicate_path:
        errors.append("duplicates existing instruction in " + duplicate_path)
    if errors:
        for error in errors:
            print("REJECT " + error)
        return 1
    if args.command == 'verify-evidence':
        try:
            verify_evidence(data, args.artifacts)
        except (OSError, ValueError) as exc:
            print('REJECT evidence: {}'.format(exc), file=sys.stderr)
            return 1
        print('Verified referenced check results. Human review is separate.')
        return 0
    if args.command == "propose":
        try:
            path = stage(data, args.output_dir)
        except (OSError, ValueError) as exc:
            print("could not stage proposal: {}".format(exc), file=sys.stderr)
            return 2
        print("Staged at {} (active skills unchanged).".format(path))
    else:
        print("ACCEPT candidate proposal {}".format(data["proposal_id"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
