"""Run positive and negative Phase 6 engineering/safety cases."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_transaction_safety import check as check_transactions, load as load_transactions  # noqa: E402
from scripts.scan_skill_security import scan_path, verdict  # noqa: E402
from scripts.validate_domain_model import load as load_domain, validate_model  # noqa: E402
from scripts.verify_spec_traceability import read_text, verify  # noqa: E402


CASES = ROOT / "tests/fixtures"


def evaluate():
    results = []
    safe_findings = scan_path(CASES / "security/safe")
    unsafe_findings = scan_path(CASES / "security/unsafe")
    results.append({
        "id": "security-safe",
        "passed": not safe_findings,
        "detail": "{} finding(s)".format(len(safe_findings)),
    })
    results.append({
        "id": "security-unsafe",
        "passed": verdict(unsafe_findings) == "reject" and len([f for f in unsafe_findings if f["severity"] == "high"]) >= 3,
        "detail": "verdict={} high={}".format(verdict(unsafe_findings), len([f for f in unsafe_findings if f["severity"] == "high"])),
    })
    domain_errors = validate_model(load_domain(CASES / "domain/order_model.yaml"))
    results.append({"id": "domain-valid", "passed": not domain_errors, "detail": "; ".join(domain_errors)})
    invalid_domain = validate_model(load_domain(CASES / "domain/order_model_invalid.yaml"))
    results.append({"id": "domain-invalid", "passed": len(invalid_domain) >= 3, "detail": "; ".join(invalid_domain)})
    spec = verify(
        read_text(CASES / "spec/requirements.md"),
        read_text(CASES / "spec/test_requirements.py"),
    )
    results.append({"id": "spec-valid", "passed": spec["valid"], "detail": "; ".join(spec["errors"])})
    invalid_spec = verify(
        read_text(CASES / "spec/requirements.md"),
        read_text(CASES / "spec/test_requirements_invalid.py"),
    )
    results.append({
        "id": "spec-invalid",
        "passed": bool(invalid_spec["missing"]) and bool(invalid_spec["orphaned"]),
        "detail": "missing={} orphaned={}".format(invalid_spec["missing"], invalid_spec["orphaned"]),
    })
    safe_tx = check_transactions(load_transactions(CASES / "transactions/safe.yaml"))
    results.append({"id": "transaction-safe", "passed": not safe_tx, "detail": "; ".join(safe_tx)})
    unsafe_tx = check_transactions(load_transactions(CASES / "transactions/unsafe.yaml"))
    results.append({"id": "transaction-unsafe", "passed": len(unsafe_tx) >= 3, "detail": "; ".join(unsafe_tx)})
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=ROOT / ".agents/artifacts/phase6")
    args = parser.parse_args(argv)
    results = evaluate()
    summary = {
        "cases": len(results),
        "passed": sum(1 for item in results if item["passed"]),
        "gate_pass": all(item["passed"] for item in results),
    }
    output = {
        "schema_version": 1,
        "run_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "results": results,
        "summary": summary,
    }
    args.artifacts.mkdir(parents=True, exist_ok=True)
    (args.artifacts / "result.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    for item in results:
        print("{} {} — {}".format("PASS" if item["passed"] else "FAIL", item["id"], item["detail"]))
    print("Phase 6: {}/{} cases passed".format(summary["passed"], summary["cases"]))
    return 0 if summary["gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
