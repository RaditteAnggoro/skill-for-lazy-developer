"""Evaluate the natural-language router with the DeepSeek Harness (DSH) CLI.

This runner is deliberately host-specific: DSH must be installed, and the selected
profile must provide model credentials plus the DSH skill, instruction, and headless
plugins. It creates a disposable workspace per case so routing cannot modify the
repository under test.
"""

import argparse
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_routing_evals import (  # noqa: E402
    load_cases,
    prepare_workspace,
    score_case,
    select_cases,
)


DEFAULT_DSH = Path("/Applications/DeepSeek Harness.app/Contents/Resources/runtime/cli/bin/dsh")
SCHEMA_KEYS = {"interaction", "primary", "supporting", "user_message"}
DSH_OVERLAY = ROOT / "adapters/dsh/AGENTS.dsh.md"


def build_command(dsh, profile):
    return [str(dsh), "--profile", profile, "-"]


def evaluation_prompt(case):
    return """Read the repository instructions and installed skill metadata. Classify the
natural-language request below without performing the requested work. Return only one
JSON object with keys interaction, primary, supporting, and user_message. interaction
must be automatic, choice, or question. Select one primary workflow and no more than
two supporting workflows. Preserve read-only and planning-only boundaries.

Request:
{}""".format(case["prompt"])


def extract_json(text):
    """Extract the first complete JSON object from a model response."""
    if not isinstance(text, str):
        raise ValueError("response must be text")
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates = [fenced.group(1)] if fenced else []
    candidates.append(text.strip())
    decoder = json.JSONDecoder()
    for candidate in candidates:
        for match in re.finditer(r"\{", candidate):
            try:
                value, end = decoder.raw_decode(candidate[match.start():])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and SCHEMA_KEYS <= set(value):
                return value
    raise ValueError("response contains no routing JSON object")


def workspace_snapshot(root):
    snapshot = {}
    root = Path(root)
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            relative = path.relative_to(root).as_posix()
            snapshot[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def run_case(case, dsh, profile, timeout, artifacts=None):
    with tempfile.TemporaryDirectory(prefix="dsh-routing-eval-") as temporary:
        workspace = Path(temporary)
        prepare_workspace(workspace)
        if DSH_OVERLAY.is_file():
            instructions = workspace / "AGENTS.md"
            instructions.write_text(
                instructions.read_text(encoding="utf-8").rstrip()
                + "\n\n"
                + DSH_OVERLAY.read_text(encoding="utf-8").rstrip()
                + "\n",
                encoding="utf-8",
            )
        before = workspace_snapshot(workspace)
        command = build_command(dsh, profile)
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"DSH_PROFILE", "DSH_PROFILE_DIR", "DSH_SESSION_ID"}
        }
        env["DSH_PERMISSION_MODE"] = "read-only"
        completed = subprocess.run(
            command,
            cwd=str(workspace),
            env=env,
            input=evaluation_prompt(case),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        if artifacts:
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / (case["id"] + ".stdout.txt")).write_text(
                completed.stdout, encoding="utf-8"
            )
            (artifacts / (case["id"] + ".stderr.txt")).write_text(
                completed.stderr, encoding="utf-8"
            )
        after = workspace_snapshot(workspace)
        differences = []
        if before != after:
            differences.append("workspace changed during read-only classification")
        if completed.returncode != 0:
            differences.append("dsh exited with {}".format(completed.returncode))
            return differences
        try:
            actual = extract_json(completed.stdout)
        except ValueError as exc:
            differences.append("invalid routing result: {}".format(exc))
            return differences
        differences.extend(score_case(case, actual))
        return differences


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsh", type=Path, default=Path(os.environ.get("DSH_BIN", DEFAULT_DSH)))
    parser.add_argument("--profile", default=os.environ.get("DSH_EVAL_PROFILE", "dsh-eval"))
    parser.add_argument("--case", action="append", dest="cases", default=[])
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args(argv)

    if not args.dsh.is_file():
        print("DSH binary not found: {}".format(args.dsh), file=sys.stderr)
        return 2
    try:
        cases = select_cases(load_cases(), args.cases)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print("Evaluation setup failed: {}".format(exc), file=sys.stderr)
        return 2

    failures = []
    for case in cases:
        try:
            differences = run_case(
                case, args.dsh, args.profile, args.timeout, args.artifacts
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            differences = [str(exc)]
        if differences:
            failures.append(case["id"])
            print("FAIL {}: {}".format(case["id"], "; ".join(differences)), flush=True)
        else:
            print("PASS {}".format(case["id"]), flush=True)

    print(
        "DSH routing evaluation: {} passed, {} failed".format(
            len(cases) - len(failures), len(failures)
        ),
        flush=True,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
