"""Deterministic Phase 1 decision harness: apply quality enhancements only when useful."""

import argparse
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]


def decide(case):
    kind = case["task_kind"]
    risk = case["risk"]
    scope = case["change_scope"]
    applied = []
    if kind == "ui_journey" and scope != "tiny":
        applied.append("exploratory_qa")
    if kind == "financial" or (risk == "high" and kind == "code_review"):
        applied.append("tdd")
    if kind in {"financial", "code_review"} and scope in {"substantial", "large"}:
        applied.append("review")
    if kind == "code_review" and scope in {"substantial", "large"}:
        applied.append("simplify")
    if kind == "requirements":
        applied.append("evidence_ledger")
    if kind == "api_failure":
        applied.append("api_layers")
    if kind == "structural":
        applied.append("ast")
    if kind == "spike":
        applied.append("spike")
    return applied


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "tests/phase1_enhancement_cases.yaml")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    cases = yaml.safe_load(args.cases.read_text(encoding="utf-8")).get("cases", [])
    results = []
    for case in cases:
        applied = decide(case)
        results.append({"id": case["id"], "applied": applied, "expected": case["expected"], "passed": sorted(applied) == sorted(case["expected"])})
    output = {"cases": len(results), "passed": sum(item["passed"] for item in results), "gate_pass": all(item["passed"] for item in results), "results": results}
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        for item in results:
            print("{} {} -> {}".format("PASS" if item["passed"] else "FAIL", item["id"], item["applied"]))
    return 0 if output["gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
