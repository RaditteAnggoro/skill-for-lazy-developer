"""Validate a multi-phase plan and its skill assignments."""

import argparse
import json
from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = "adaptive-workflow"


def known_skills(root=ROOT):
    return {
        path.parent.name
        for path in (Path(root) / ".agents/skills").glob("*/SKILL.md")
    }


def _ancestors(phase_id, dependencies):
    seen = set()
    pending = list(dependencies.get(phase_id, []))
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(dependencies.get(current, []))
    return seen


def validate_plan(data, skills=None, require_final=True):
    skills = known_skills() if skills is None else set(skills)
    errors = []
    if not isinstance(data, dict):
        return ["plan must be a mapping"]
    phases = data.get("phases")
    if not isinstance(phases, list) or not phases:
        return ["phases must be a nonempty list"]

    valid = []
    ids = []
    for index, phase in enumerate(phases):
        prefix = "phase {}".format(index)
        if not isinstance(phase, dict):
            errors.append(prefix + " must be a mapping")
            continue
        phase_id = phase.get("id")
        if not isinstance(phase_id, str) or not phase_id.strip():
            errors.append(prefix + " id must be a nonempty string")
        elif phase_id in ids:
            errors.append("duplicate phase id: {}".format(phase_id))
        else:
            ids.append(phase_id)
        for key in ("primary", "entry", "exit", "evidence"):
            if not isinstance(phase.get(key), str) or not phase.get(key).strip():
                errors.append(prefix + " missing or invalid " + key)
        primary = phase.get("primary")
        if primary == ORCHESTRATOR:
            errors.append(prefix + " cannot use the router as a work skill")
        elif isinstance(primary, str) and primary not in skills:
            errors.append(prefix + " has unknown primary skill: {}".format(primary))
        support = phase.get("support", [])
        if not isinstance(support, list) or len(support) > 2:
            errors.append(prefix + " support must be a list of at most two skills")
            support = []
        elif not all(isinstance(name, str) and name for name in support):
            errors.append(prefix + " support must contain nonempty strings")
            support = [name for name in support if isinstance(name, str) and name]
        if len(set(support)) != len(support):
            errors.append(prefix + " has duplicate support skills")
        if primary in support:
            errors.append(prefix + " repeats primary as support")
        for name in support:
            if name == ORCHESTRATOR:
                errors.append(prefix + " cannot use the router as a support skill")
            elif name not in skills:
                errors.append(prefix + " has unknown support skill: {}".format(name))
        depends = phase.get("depends_on", [])
        if not isinstance(depends, list):
            errors.append(prefix + " depends_on must be a list")
            depends = []
        elif not all(isinstance(name, str) and name for name in depends):
            errors.append(prefix + " depends_on must contain nonempty strings")
            depends = [name for name in depends if isinstance(name, str) and name]
        if len(set(depends)) != len(depends):
            errors.append(prefix + " has duplicate dependencies")
        valid.append((index, phase_id, primary, depends))

    id_to_index = {
        phase_id: index
        for index, phase_id, _, _ in valid
        if isinstance(phase_id, str) and phase_id
    }
    dependencies = {}
    for index, phase_id, _, depends in valid:
        if not isinstance(phase_id, str) or not phase_id:
            continue
        dependencies[phase_id] = depends
        if index > 0 and not depends:
            errors.append("phase {} must declare depends_on".format(phase_id))
        for dependency in depends:
            if dependency not in id_to_index:
                errors.append("{} depends on unknown phase {}".format(phase_id, dependency))
            elif id_to_index[dependency] >= index:
                errors.append("{} must depend on an earlier phase".format(phase_id))

    if require_final and phases:
        last = phases[-1]
        if not isinstance(last, dict):
            errors.append("final phase must be a mapping")
        elif last.get("primary") != "verification-before-completion":
            errors.append("final phase must use verification-before-completion")
        elif not last.get("depends_on"):
            errors.append("final verification must depend on completed work")
        else:
            final_id = last.get("id")
            if not isinstance(final_id, str) or not final_id:
                errors.append("final phase id must be a nonempty string")
                return errors
            final_dependencies = dependencies.get(final_id, [])
            final_ancestors = _ancestors(final_id, dependencies)
            missing = [
                phase_id
                for index, phase_id, _, _ in valid
                if isinstance(phase_id, str) and phase_id and phase_id != final_id
                and phase_id not in final_ancestors
            ]
            if missing:
                errors.append("final verification must depend on all work phases; missing: " + ", ".join(missing))
            if not final_dependencies:
                errors.append("final verification has no direct dependency")
    return errors


def validate_case(case, skills=None):
    errors = []
    if not case.get("task") or not case.get("authorized_scope"):
        errors.append("case needs task and authorized_scope")
    plan = case.get("plan")
    if not isinstance(plan, dict):
        errors.append("case needs a plan mapping")
        return errors
    errors.extend(validate_plan(plan, skills=skills, require_final=case.get("require_final", True)))
    expected = case.get("expected_phases")
    if expected:
        actual = [phase.get("primary") for phase in plan.get("phases", []) if isinstance(phase, dict)]
        if actual != expected:
            errors.append("expected phases {}, got {}".format(expected, actual))
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "tests/orchestration_cases.yaml")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    data = yaml.safe_load(args.cases.read_text(encoding="utf-8"))
    cases = data.get("cases") if isinstance(data, dict) else None
    if not isinstance(cases, list) or not cases:
        print("cases file needs a nonempty cases list", file=sys.stderr)
        return 2
    skills = known_skills()
    results = [
        {"id": case.get("id", "case-{}".format(index)), "errors": validate_case(case, skills)}
        for index, case in enumerate(cases)
    ]
    output = {"valid": all(not item["errors"] for item in results), "results": results}
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        for item in results:
            print("{} {}".format("PASS" if not item["errors"] else "FAIL", item["id"]))
            for error in item["errors"]:
                print("  " + error)
    return 0 if output["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
