"""Check that each requirement ID has at least one test reference."""

import argparse
import json
from pathlib import Path
import re
import sys


REQUIREMENT = re.compile(r"\bREQ-\d{3,}\b")
REFERENCE = re.compile(r"\bREQ-\d{3,}\b")


def read_text(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def requirements(spec_text):
    found = []
    for line in spec_text.splitlines():
        if re.match(r"^\s*[-*]?\s*REQ-\d{3,}\b", line, re.I):
            found.extend(match.group(0).upper() for match in REQUIREMENT.finditer(line))
    return list(dict.fromkeys(found))


def evidence(tests_text):
    return {match.group(0).upper() for match in REFERENCE.finditer(tests_text)}


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
        "requirements": required,
        "covered": sorted(covered),
        "missing": missing,
        "orphaned": orphaned,
        "errors": errors,
        "valid": not errors,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("tests", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = verify(read_text(args.spec), read_text(args.tests))
    except OSError as exc:
        print("verification failed: {}".format(exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif result["valid"]:
        print("Traceability passed for {} requirement(s).".format(len(result["requirements"])))
    else:
        for error in result["errors"]:
            print("FAIL " + error)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
