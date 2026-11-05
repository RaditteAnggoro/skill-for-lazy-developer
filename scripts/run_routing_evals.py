"""Run repeatable, read-only model trials for the natural-language router."""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tests/routing_cases.yaml"
SCHEMA = ROOT / "tests/routing_result.schema.json"
FORBIDDEN_BOILERPLATE = (
    "as an ai",
    "sebagai ai",
    "great idea",
    "i acknowledge your request",
    "your request has been received",
    "would you like me to",
    "apakah anda ingin saya",
    "permintaan anda telah diterima",
    "berdasarkan instruksi yang diberikan",
)


def load_cases(path=CASES):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return data["cases"]


def select_cases(cases, requested):
    if not requested:
        return cases
    by_id = {case["id"]: case for case in cases}
    missing = sorted(set(requested) - set(by_id))
    if missing:
        raise ValueError("unknown case id: {}".format(", ".join(missing)))
    return [by_id[case_id] for case_id in requested]


def build_command(codex, workspace, result, model=None):
    command = [
        codex,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--output-schema",
        str(SCHEMA),
        "--output-last-message",
        str(result),
        "--json",
        "--cd",
        str(workspace),
    ]
    if model:
        command.extend(["--model", model])
    return command


def evaluation_prompt(case):
    return """Read the repository instructions and installed skill metadata. Classify the
natural-language request below without performing the requested work. Return only the
required routing JSON. Preserve read-only and planning-only boundaries. Select one
primary workflow and no more than two supporting workflows.

Request:
{}""".format(case["prompt"])


def score_case(case, actual):
    differences = []
    accepted_interactions = case.get("accepted_interactions", [case["interaction"]])
    if actual.get("interaction") not in accepted_interactions:
        differences.append(
            "interaction expected one of {!r}, got {!r}".format(
                accepted_interactions, actual.get("interaction")
            )
        )
    for key in ("primary", "supporting"):
        expected = case.get(key, [])
        if actual.get(key) != expected:
            differences.append(
                "{} expected {!r}, got {!r}".format(key, expected, actual.get(key))
            )
    differences.extend(score_message(case, actual.get("user_message")))
    return differences


def score_message(case, message):
    if not isinstance(message, str) or not message.strip():
        return ["user_message must be a nonempty string"]
    differences = []
    lowered = message.casefold()
    for phrase in FORBIDDEN_BOILERPLATE:
        if phrase in lowered:
            differences.append("user_message contains boilerplate {!r}".format(phrase))

    expected = case.get("message_expectations")
    if not expected:
        return differences
    words = re.findall(r"\b[\w'-]+\b", message, flags=re.UNICODE)
    if len(words) > expected["max_words"]:
        differences.append(
            "user_message has {} words, maximum is {}".format(
                len(words), expected["max_words"]
            )
        )
    question = expected["question"]
    if question == "required" and "?" not in message:
        differences.append("user_message must ask one concise question")
    if question == "forbidden" and "?" in message:
        differences.append("user_message must continue without a redundant question")
    if expected["language"] == "id":
        markers = {"saya", "akan", "dan", "yang", "untuk", "lalu", "penyebab"}
        if not markers.intersection(word.casefold() for word in words):
            differences.append("user_message does not appear to use Indonesian")
    required_any = [item.casefold() for item in expected.get("required_any", [])]
    if required_any and not any(item in lowered for item in required_any):
        differences.append(
            "user_message must mention one of {!r}".format(required_any)
        )
    return differences


def prepare_workspace(destination):
    shutil.copytree(
        ROOT / ".agents",
        destination / ".agents",
        ignore=shutil.ignore_patterns("artifacts", "__pycache__"),
    )
    shutil.copy2(ROOT / "AGENTS.snippet.md", destination / "AGENTS.md")


def run_case(case, codex, model, timeout, artifacts=None):
    with tempfile.TemporaryDirectory(prefix="routing-eval-") as temporary:
        workspace = Path(temporary)
        prepare_workspace(workspace)
        result = workspace / "result.json"
        command = build_command(codex, workspace, result, model)
        completed = subprocess.run(
            command,
            input=evaluation_prompt(case),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        trace = completed.stdout
        if artifacts:
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / (case["id"] + ".jsonl")).write_text(trace, encoding="utf-8")
            (artifacts / (case["id"] + ".stderr.txt")).write_text(
                completed.stderr, encoding="utf-8"
            )
        if completed.returncode != 0:
            return ["codex exited with {}".format(completed.returncode)]
        try:
            actual = json.loads(result.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return ["invalid routing result: {}".format(exc)]
        return score_case(case, actual)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", dest="cases", default=[])
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()

    try:
        cases = select_cases(load_cases(), args.cases)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print("Evaluation setup failed: {}".format(exc), file=sys.stderr)
        return 2

    failures = []
    for case in cases:
        try:
            differences = run_case(
                case, args.codex, args.model, args.timeout, args.artifacts
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            differences = [str(exc)]
        if differences:
            failures.append(case["id"])
            print(
                "FAIL {}: {}".format(case["id"], "; ".join(differences)),
                flush=True,
            )
        else:
            print("PASS {}".format(case["id"]), flush=True)

    print(
        "Routing evaluation: {} passed, {} failed".format(
            len(cases) - len(failures), len(failures)
        ),
        flush=True,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
