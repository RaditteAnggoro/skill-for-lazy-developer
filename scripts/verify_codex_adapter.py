"""Run an end-to-end Codex lifecycle check for the memory adapter.

The test uses a disposable CODEX_HOME and project, a real Engram binary, and the
Codex CLI. Hooks are run with --dangerously-bypass-hook-trust for automation; normal
users must review the hooks once with /hooks.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.codex.memory_runtime import (  # noqa: E402
    RECORD_ENVELOPE, base_record, project_for, provider_project, recall as read_memory, save_record,
)
from scripts.install_codex_adapter import install, uninstall  # noqa: E402


DEFAULT_CODEX = Path(
    "/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex"
)


class VerifyError(RuntimeError):
    pass


def run(command, cwd=None, env=None, timeout=60):
    completed = subprocess.run(
        [str(item) for item in command],
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise VerifyError(
            "{} failed: {}".format(
                " ".join(str(item) for item in command[:3]),
                (completed.stderr or completed.stdout)[-1600:],
            )
        )
    return completed


def codex_exec(codex, home, project, prompt, timeout):
    env = dict(os.environ)
    env["CODEX_HOME"] = str(home)
    env["CODEX_MEMORY_CONFIG"] = str(home / "codex-memory/config.json")
    return run(
        [
            codex,
            "exec",
            "--dangerously-bypass-hook-trust",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "-C",
            project,
            prompt,
        ],
        cwd=project,
        env=env,
        timeout=timeout,
    )


def engram(config, data_dir, project, args, timeout=30):
    env = dict(os.environ)
    env["ENGRAM_DATA_DIR"] = str(data_dir)
    return run(
        [config, *args],
        cwd=project,
        env=env,
        timeout=timeout,
    )


def verify(codex, engram_bin, artifacts, timeout, model=None):
    artifacts = Path(artifacts).resolve()
    root = artifacts / "codex-adapter-verification"
    if root.exists():
        raise VerifyError("Choose a new artifacts directory for this run")
    home = root / "codex-home"
    project = root / "project"
    data = root / "engram-data"
    project.mkdir(parents=True)
    data.mkdir(parents=True)
    home.mkdir(parents=True)
    (project / "AGENTS.md").write_text(
        "# Codex adapter verification\n\nUse project memory when relevant.\n",
        encoding="utf-8",
    )
    (project / "test_probe.py").write_text(
        "import unittest\n\n\nclass Probe(unittest.TestCase):\n"
        "    def test_fixture(self):\n        self.assertEqual(7, 7)\n",
        encoding="utf-8",
    )
    auth_source = Path.home() / ".codex/auth.json"
    if not auth_source.is_file():
        raise VerifyError("Codex auth.json is unavailable; cannot run the model")
    (home / "auth.json").symlink_to(auth_source)
    (home / "config.toml").write_text(
        "model = \"{}\"\nmodel_reasoning_effort = \"low\"\n\n[features]\nhooks = true\n".format(
            model or "gpt-6.1-sol"
        ),
        encoding="utf-8",
    )
    engram(config=engram_bin, data_dir=data, project=project, args=["init", "demo"])
    install(home, str(engram_bin), str(data))
    scope = project_for(project)
    namespace = provider_project(scope)
    seed = base_record("decision", "seed/recall", "Seed memory", "The project recall token is RECALL-TOKEN-7319.",
                       "verified", 1.0, "user", project_name=scope["name"])
    provider = {"engram_bin": str(engram_bin), "data_dir": str(data)}
    if not save_record(provider, scope, seed, "decision", project):
        raise VerifyError("Could not seed isolated Engram memory")

    result = {
        "schema_version": 1,
        "run_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "codex_home": str(home),
        "project": str(project),
        "checks": {},
    }

    recall = codex_exec(
        codex,
        home,
        project,
        "If your context contains a token starting with RECALL-TOKEN-, reply with that token only. Otherwise reply NONE.",
        timeout,
    )
    result["recall"] = {
        "stdout": recall.stdout.strip(),
        "passed": "RECALL-TOKEN-7319" in recall.stdout,
    }

    remember = codex_exec(
        codex,
        home,
        project,
        "Remember this: Phase 3 uses a bounded handoff. Then reply with two sentences confirming the adapter test is complete.",
        timeout,
    )
    remembered = engram(
        config=engram_bin,
        data_dir=data,
        project=project,
        args=["search", "Phase 3 uses a bounded handoff", "--project", namespace, "--limit", "5"],
    )
    result["remember"] = {
        "stdout": remember.stdout.strip(),
        "stored": "Phase 3 uses a bounded handoff" in remembered.stdout,
    }

    codex_exec(
        codex, home, project,
        "Run exactly python3 -m unittest discover in this synthetic project. If it passes, reply: "
        "Verification: python3 -m unittest discover passed. The synthetic fixture is verified and ready.",
        timeout,
    )
    records = [json.loads(match.group(1)) for match in RECORD_ENVELOPE.finditer(read_memory(provider, scope, project))]
    handoffs = [record for record in records if record.get("kind") == "handoff"]
    result["handoff"] = {
        "stored": bool(handoffs),
        "verified": any(record.get("trust") == "verified" for record in handoffs),
    }
    result["checks"]["recall"] = result["recall"]["passed"]
    result["checks"]["remember"] = result["remember"]["stored"]
    result["checks"]["handoff"] = all(result["handoff"].values())

    config_path = home / "codex-memory/config.json"
    original_config = json.loads(config_path.read_text(encoding="utf-8"))
    broken = dict(original_config)
    broken["engram_bin"] = str(root / "missing-engram")
    config_path.write_text(json.dumps(broken, indent=2) + "\n", encoding="utf-8")
    failed_open = codex_exec(codex, home, project, "Reply with exactly: OK", timeout)
    result["fail_open"] = {
        "stdout": failed_open.stdout.strip(),
        "passed": "OK" in failed_open.stdout,
    }
    result["checks"]["fail_open"] = result["fail_open"]["passed"]
    config_path.write_text(json.dumps(original_config, indent=2) + "\n", encoding="utf-8")

    opt_out = codex_exec(
        codex,
        home,
        project,
        "Do not remember this project. Reply with exactly: OK",
        timeout,
    )
    config_after = json.loads(config_path.read_text(encoding="utf-8"))
    result["opt_out"] = {
        "stdout": opt_out.stdout.strip(),
        "recorded": str(project.resolve()) in config_after.get("opt_outs", []),
    }
    result["checks"]["opt_out"] = result["opt_out"]["recorded"]

    uninstall(home)
    result["uninstall"] = {
        "hooks_removed": "memory_runtime.py" not in (home / "hooks.json").read_text(encoding="utf-8"),
        "runtime_removed": not (home / "codex-memory/memory_runtime.py").exists(),
    }
    result["checks"]["uninstall"] = all(result["uninstall"].values())
    result["ok"] = all(result["checks"].values())
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "codex-verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", type=Path, default=DEFAULT_CODEX)
    parser.add_argument("--engram-bin", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, default=ROOT / ".agents/artifacts/codex-verification")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--model")
    args = parser.parse_args(argv)
    if not args.codex.is_file():
        print("Codex binary not found: {}".format(args.codex), file=sys.stderr)
        return 2
    if not args.engram_bin.is_file():
        print("Engram binary not found: {}".format(args.engram_bin), file=sys.stderr)
        return 2
    try:
        result = verify(
            args.codex, args.engram_bin, args.artifacts, args.timeout, args.model
        )
    except (OSError, VerifyError, subprocess.TimeoutExpired) as exc:
        print("Codex adapter verification failed: {}".format(exc), file=sys.stderr)
        return 1
    print(json.dumps(result["checks"], indent=2))
    print("Codex adapter verification: {}".format("PASS" if result["ok"] else "FAIL"))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
