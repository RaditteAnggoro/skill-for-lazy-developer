"""Measure selective context assembly against full-context baselines."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.context_optimizer import run, summarize  # noqa: E402


CASES = ROOT / "tests/token_optimization_cases.yaml"
DEFAULT_ARTIFACTS = ROOT / ".agents/artifacts/phase4-token"


def load_cases(path):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError("token corpus must contain a cases array")
    if not data["cases"]:
        raise ValueError("token corpus must not be empty")
    return data["cases"]


def format_report(result):
    lines = [
        "# Token optimization benchmark",
        "",
        "Run at: `{}`".format(result["run_at"]),
        "",
        "| Case | Baseline tokens | Optimized tokens | Reduction | Facts | Constraints | Raw tool | Raw source |",
        "| --- | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    for item in result["cases"]:
        lines.append(
            "| {} | {} | {} | {:.2f}% | {} | {} | {} | {} |".format(
                item["id"],
                item["baseline_tokens"],
                item["optimized_tokens"],
                item["reduction_percent"],
                "pass" if item["correct"] else "FAIL",
                "pass" if item["constraints_preserved"] else "FAIL",
                "pass" if item["raw_tool_recovered"] else "FAIL",
                "pass" if item["raw_source_recovered"] else "FAIL",
            )
        )
    summary = result["summary"]
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "- Cases: **{}**".format(summary["cases"]),
            "- Encoding: `{}`".format(summary["encoding"]),
            "- Median context reduction: **{:.2f}%**".format(summary["median_reduction_percent"]),
            "- Minimum reduction: **{:.2f}%**".format(summary["min_reduction_percent"]),
            "- Correct facts retained: **{}**".format(summary["correct_cases"]),
            "- Critical constraints preserved: **{}**".format(summary["constraints_preserved"]),
            "- Raw evidence recovered: **{}**".format(
                summary["raw_tool_recovered"] and summary["raw_source_recovered"]
            ),
            "- Gate: **{}**".format("PASS" if summary["gate_pass"] else "FAIL"),
            "",
            "The measurement is a context-retention benchmark, not a live model-answer",
            "quality benchmark. Every required fact and every critical constraint is checked",
            "against the optimized context; full tool and source evidence remain readable",
            "through the recorded `raw://` references.",
        ]
    )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=CASES)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    args = parser.parse_args(argv)
    cases = load_cases(args.cases)
    artifacts = args.artifacts.resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    results = run(cases, artifacts / "raw")
    summary = summarize(results)
    output = {
        "schema_version": 1,
        "run_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "corpus": str(args.cases),
        "encoding": summary["encoding"],
        "cases": results,
        "summary": summary,
    }
    (artifacts / "result.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = format_report(output)
    (artifacts / "result.md").write_text(report + "\n", encoding="utf-8")
    print(report)
    return 0 if summary["gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
