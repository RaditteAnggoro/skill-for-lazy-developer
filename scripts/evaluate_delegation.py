"""Deterministic decision harness for selective specialist delegation."""

import argparse
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]


def decide(case):
    if not case.get("independent") or case.get("consequence") == "low":
        return "single", None
    if not case.get("host_supported") or not case.get("permissions_readonly"):
        return "fallback", case.get("role")
    return "delegate", case.get("role")


def trace(case):
    """Return a labelled trace; no host is invoked by this harness."""
    decision, role = decide(case)
    if decision == "single":
        return {
            "id": case["id"], "decision": decision, "role": None,
            "execution_mode": "single-agent", "live_dispatch": False,
            "fallback_reason": None, "evidence_level": "SIMULATED",
        }
    if decision == "fallback":
        reason = "host_no_delegation" if not case.get("host_supported") else "permission_restricted"
        return {
            "id": case["id"], "decision": decision, "role": role,
            "execution_mode": "single-agent-role-guided", "live_dispatch": False,
            "fallback_reason": reason, "evidence_level": "SIMULATED",
        }
    return {
        "id": case["id"], "decision": decision, "role": role,
        "execution_mode": "simulated-delegation", "live_dispatch": False,
        "fallback_reason": None, "evidence_level": "SIMULATED",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "tests/delegation_cases.yaml")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    cases = yaml.safe_load(args.cases.read_text(encoding="utf-8")).get("cases", [])
    results = []
    for case in cases:
        record = trace(case)
        record["expected"] = case["expected"]
        record["expected_role"] = case.get("role")
        record["passed"] = record["decision"] == case["expected"] and record["role"] == case.get("role")
        results.append(record)
    output = {"cases": len(results), "passed": sum(item["passed"] for item in results),
              "gate_pass": all(item["passed"] for item in results), "results": results}
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        for item in results:
            print("{} {} -> {}{}".format("PASS" if item["passed"] else "FAIL", item["id"], item["decision"], " " + item["role"] if item["role"] else ""))
    return 0 if output["gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
