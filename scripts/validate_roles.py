"""Validate provider-neutral role contracts before generating host adapters."""

import argparse
import json
from pathlib import Path
import re
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
ROLES = ROOT / ".agents/roles"
ID = re.compile(r"^ld-[a-z0-9-]+$")
EXPECTED = {
    "ld-codebase-explorer",
    "ld-independent-test-reviewer",
    "ld-financial-integrity-reviewer",
    "ld-workflow-tool-evaluator",
}
FIELDS = {
    "id", "version", "purpose", "trigger", "scopes", "write_permission",
    "external_side_effects", "required_evidence", "allowed_capabilities",
    "optional_capabilities", "denied_capabilities", "output_contract", "fallback",
}
SCOPES = {"analysis", "review", "verification", "exploration", "evaluation"}
STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_TESTED"}


def validate_role(data, filename="<role>"):
    errors = []
    if not isinstance(data, dict):
        return [filename + ": role must be a mapping"]
    unknown = sorted(set(data) - FIELDS)
    missing = sorted(FIELDS - set(data))
    if unknown:
        errors.append("unknown fields: " + ", ".join(unknown))
    if missing:
        errors.append("missing fields: " + ", ".join(missing))
    role_id = data.get("id")
    if not isinstance(role_id, str) or not ID.fullmatch(role_id):
        errors.append("id must match ld-[a-z0-9-]+")
    if data.get("version") != 1:
        errors.append("version must be 1")
    if not isinstance(data.get("purpose"), str) or not data["purpose"].strip():
        errors.append("purpose must be nonempty")
    trigger = data.get("trigger")
    if not isinstance(trigger, dict) or set(trigger) != {"when", "avoid"}:
        errors.append("trigger must contain when and avoid")
    else:
        for key in ("when", "avoid"):
            if not isinstance(trigger[key], list) or not trigger[key] or not all(isinstance(item, str) and item for item in trigger[key]):
                errors.append("trigger.{} must be a nonempty string list".format(key))
    scopes = data.get("scopes")
    if not isinstance(scopes, list) or not scopes or not set(scopes) <= SCOPES:
        errors.append("invalid scopes")
    if data.get("write_permission") is not False:
        errors.append("initial roles must have write_permission false")
    if data.get("external_side_effects") is not False:
        errors.append("initial roles must have external_side_effects false")
    for key in ("required_evidence", "allowed_capabilities", "optional_capabilities", "denied_capabilities"):
        value = data.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            errors.append(key + " must be a string list")
    allowed = set(data.get("allowed_capabilities") or [])
    denied = set(data.get("denied_capabilities") or [])
    optional = set(data.get("optional_capabilities") or [])
    if allowed & denied or optional & denied:
        errors.append("allowed/optional capabilities must not overlap denied capabilities")
    if not {"filesystem-write", "remote-push"} <= denied:
        errors.append("denied capabilities must include filesystem-write and remote-push")
    output = data.get("output_contract")
    if not isinstance(output, dict) or set(output) != {"sections", "status", "cite_source_locations"}:
        errors.append("output_contract requires sections, status, cite_source_locations")
    else:
        if not isinstance(output["sections"], list) or not output["sections"]:
            errors.append("output sections must be nonempty")
        if not isinstance(output["status"], list) or not set(output["status"]) <= STATUSES:
            errors.append("invalid output status")
        if output["cite_source_locations"] is not True:
            errors.append("output must cite source locations")
    if not isinstance(data.get("fallback"), str) or not data["fallback"].strip():
        errors.append("fallback must be nonempty")
    return ["{}: {}".format(filename, error) for error in errors]


def load_roles(root=ROLES):
    roles = []
    for path in sorted(Path(root).glob("*.yaml")):
        if path.name == "schema.yaml":
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            roles.append((path, {"__error__": str(exc)}))
            continue
        roles.append((path, data))
    return roles


def validate_all(root=ROLES):
    errors = []
    roles = load_roles(root)
    ids = []
    for path, data in roles:
        if "__error__" in data:
            errors.append("{}: {}".format(path.name, data["__error__"]))
            continue
        errors.extend(validate_role(data, path.name))
        if isinstance(data, dict) and isinstance(data.get("id"), str):
            ids.append(data["id"])
    if len(ids) != len(set(ids)):
        errors.append("duplicate role ids")
    missing = sorted(EXPECTED - set(ids))
    if missing:
        errors.append("missing required roles: " + ", ".join(missing))
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROLES)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    errors = validate_all(args.root)
    if args.json:
        print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    elif errors:
        for error in errors:
            print("FAIL " + error)
    else:
        print("Validated {} role contract(s).".format(len(load_roles(args.root))))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
