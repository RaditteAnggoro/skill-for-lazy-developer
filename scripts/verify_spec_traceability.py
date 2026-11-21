"""Check requirement references and optionally require executed JUnit results."""

import argparse
import json
from pathlib import Path
import re
import sys
from xml.etree import ElementTree


REQUIREMENT = re.compile(r"\bREQ-\d{3,}\b", re.I)
MAX_JUNIT_BYTES = 10 * 1024 * 1024


def read_text(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def requirements(spec_text):
    found = []
    for line in spec_text.splitlines():
        if re.match(r"^\s*[-*]?\s*REQ-\d{3,}\b", line, re.I):
            found.extend(match.group(0).upper() for match in REQUIREMENT.finditer(line))
    return list(dict.fromkeys(found))


def evidence(tests_text):
    return {match.group(0).upper() for match in REQUIREMENT.finditer(tests_text)}


def verify(spec_text, tests_text):
    required = requirements(spec_text)
    covered = evidence(tests_text)
    missing = [req for req in required if req not in covered]
    orphaned = sorted(covered - set(required))
    errors = []
    if not required:
        errors.append("no requirements found")
    if missing:
        errors.append("requirements without evidence: " + ", ".join(missing))
    if orphaned:
        errors.append("test references without a requirement: " + ", ".join(orphaned))
    return {
        "evidence_level": "reference_only",
        "requirements": required,
        "covered": sorted(covered),
        "missing": missing,
        "orphaned": orphaned,
        "errors": errors,
        "valid": not errors,
    }


def junit_outcomes(path):
    with path.open("rb") as stream:
        data = stream.read(MAX_JUNIT_BYTES + 1)
    if len(data) > MAX_JUNIT_BYTES:
        raise ValueError("JUnit report exceeds the size limit")
    text = data.decode("utf-8-sig")
    if re.search(r"<!DOCTYPE|<!ENTITY", text, re.I):
        raise ValueError("JUnit report must not contain a DTD or entities")
    root = ElementTree.fromstring(text)
    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError("expected a JUnit testsuite or testsuites root")
    outcomes = {}
    for case in root.iter("testcase"):
        name = case.get("name", "")
        if not name:
            raise ValueError("JUnit testcase requires a name")
        suite = case.get("classname")
        identifier = f"{suite}::{name}" if suite else name
        if identifier in outcomes:
            raise ValueError("duplicate JUnit testcase: " + identifier)
        recorded = case.get("status", "").strip().lower()
        if recorded in {"failed", "failure", "error"} or any(
                case.find(tag) is not None for tag in ("error", "failure")):
            outcomes[identifier] = "failed"
        elif case.find("skipped") is not None or recorded not in {
                "", "run", "passed", "success", "complete", "completed"}:
            outcomes[identifier] = "skipped"
        else:
            outcomes[identifier] = "passed"
    if not outcomes:
        raise ValueError("JUnit report contains no testcases")
    return outcomes


def verify_execution(spec_text, mapping, outcomes):
    required = requirements(spec_text)
    if not required:
        raise ValueError("no requirements found")
    if not isinstance(mapping, dict) or set(mapping) != set(required):
        raise ValueError("assertion map must contain exactly the declared requirement IDs")
    results = []
    for req in required:
        checks = mapping[req]
        if (not isinstance(checks, list) or not checks
                or not all(isinstance(check, str) and check.strip() for check in checks)
                or len(set(checks)) != len(checks)):
            raise ValueError("expected unique testcase identifiers for " + req)
        observations = {check: outcomes.get(check, "missing") for check in checks}
        observed = set(observations.values())
        status = "unverified"
        if "failed" in observed:
            status = "failed"
        elif observed == {"passed"}:
            status = "passed"
        results.append({"id": req, "status": status, "observations": observations})
    return {"evidence_level": "junit_results", "results": results,
            "valid": all(row["status"] == "passed" for row in results)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("tests", type=Path, nargs="?")
    parser.add_argument("--assertion-map", type=Path)
    parser.add_argument("--junit", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    execution = args.junit is not None or args.assertion_map is not None
    if execution and (args.junit is None or args.assertion_map is None or args.tests is not None):
        parser.error("supply --assertion-map and --junit together, without a test source")
    if not execution and args.tests is None:
        parser.error("supply a test source or an assertion map and JUnit report")
    try:
        spec = read_text(args.spec)
        if execution:
            result = verify_execution(spec, json.loads(read_text(args.assertion_map)), junit_outcomes(args.junit))
        else:
            result = verify(spec, read_text(args.tests))
    except (OSError, ValueError, ElementTree.ParseError) as exc:
        print("verification failed: {}".format(exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif execution:
        for row in result["results"]:
            print("{} {}".format(row["status"].upper(), row["id"]))
    elif result["valid"]:
        print("Reference lint passed for {} requirement(s). No execution evidence checked.".format(len(result["requirements"])))
    else:
        for error in result["errors"]:
            print("FAIL " + error)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
