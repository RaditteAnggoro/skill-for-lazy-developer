"""Simulate single-agent phase execution from a validated phase plan.

This is a deterministic harness, not a live model run. It proves plan ordering, skill
loading labels, and the final trace shape without claiming agent behaviour.
"""

import argparse
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_phase_plan import known_skills, validate_plan  # noqa: E402


def simulate(plan, skills=None):
    errors = validate_plan(plan, skills=skills)
    if errors:
        raise ValueError("; ".join(errors))
    phases = plan["phases"]
    trace = []
    for phase in phases:
        trace.append({
            "phase": phase["id"],
            "skill": phase["primary"],
            "support": list(phase.get("support", [])),
            "status": "completed",
            "evidence": phase["evidence"],
        })
    final = trace[-1]
    report = "\n".join(
        "| {} | `{}` | {} |".format(item["phase"], item["skill"], item["evidence"])
        for item in trace
    )
    return {
        "trace": trace,
        "asked_user_between_phases": False,
        "final_phase": final["phase"],
        "final_report": report,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "tests/orchestration_cases.yaml")
    parser.add_argument("--id", default="invoice-backend-and-ui")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    data = yaml.safe_load(args.cases.read_text(encoding="utf-8"))
    cases = data.get("cases") if isinstance(data, dict) else None
    case = next((item for item in (cases or []) if item.get("id") == args.id), None)
    if case is None:
        print("case not found: {}".format(args.id), file=sys.stderr)
        return 2
    try:
        result = simulate(case["plan"], known_skills())
    except ValueError as exc:
        print("invalid plan: {}".format(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["final_report"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
