#!/usr/bin/env python3
"""Codex lifecycle hooks for project memory.

The script is deliberately small and fail-open. It reads one Codex hook event from
stdin, emits only the JSON that Codex understands, and never prints a traceback to
stdout. Engram is the storage provider; the project must have an `.engram/config.json`.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


RUNTIME_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = RUNTIME_DIR / "config.json"
SENSITIVE = (
    re.compile(r"\bsk-(?:proj-|test-)?[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~-]{20,}"),
    re.compile(
        r"(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)"
        r"\s*[:=]\s*\S{6,}"
    ),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
)

VERIFY_COMMAND = re.compile(
    r"\b(pytest|python -m pytest|npm test|pnpm test|yarn test|go test|cargo test|"
    r"dotnet test|mvn test|gradle test|rspec|phpunit|ruff|eslint|lint|"
    r"typecheck|tsc|build|check)\b",
    re.IGNORECASE,
)
VERIFY_SUCCESS = re.compile(
    r"(\bpassed\b|\bpass\b|\bsuccess(?:ful|fully)?\b|\bsucceeded\b|\bok\b|"
    r"exit(?:ed)?\s*(?:code\s*)?0|0\s+failed|no\s+errors)",
    re.IGNORECASE,
)


def read_config():
    path = Path(os.environ.get("CODEX_MEMORY_CONFIG", DEFAULT_CONFIG))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"engram_bin": "engram", "data_dir": None, "opt_outs": []}
    if not isinstance(data, dict):
        return {"engram_bin": "engram", "data_dir": None, "opt_outs": []}
    data.setdefault("engram_bin", "engram")
    data.setdefault("data_dir", None)
    data.setdefault("opt_outs", [])
    if not isinstance(data["opt_outs"], list):
        data["opt_outs"] = []
    return data


def write_config(config):
    path = Path(os.environ.get("CODEX_MEMORY_CONFIG", DEFAULT_CONFIG))
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def sensitive(text):
    return any(pattern.search(text) for pattern in SENSITIVE)


def project_for(cwd):
    current = Path(cwd).resolve()
    for candidate in (current, *current.parents):
        config = candidate / ".engram/config.json"
        if config.is_file():
            try:
                data = json.loads(config.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
            name = data.get("project_name")
            if isinstance(name, str) and name.strip():
                return {"root": str(candidate), "name": name.strip()}
    return None


def engram(config, args, cwd, timeout=3):
    command = [str(config.get("engram_bin") or "engram"), *args]
    env = dict(os.environ)
    if config.get("data_dir"):
        env["ENGRAM_DATA_DIR"] = str(config["data_dir"])
    return subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        input=None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def recall(config, project, cwd):
    completed = engram(config, ["context", project["name"]], cwd, timeout=4)
    if completed.returncode != 0:
        return ""
    text = completed.stdout.strip()
    if not text or "No memories" in text:
        return ""
    if sensitive(text):
        return ""
    return text[-1800:]


def envelope(record):
    meta = {
        "id": record["id"],
        "kind": record["kind"],
        "topic": record["topic"],
        "status": record["status"],
        "trust": record["trust"],
        "confidence": record["confidence"],
        "scope": record["scope"],
    }
    return "<!-- memory-record:v1 {} -->\n# {}\n\n{}\n".format(
        json.dumps(meta, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        record["title"],
        record["content"].strip(),
    )


def save_record(config, project, record, engram_type, cwd, timeout=3):
    completed = engram(
        config,
        [
            "save",
            record["title"],
            envelope(record),
            "--type",
            engram_type,
            "--project",
            project["name"],
            "--scope",
            "project",
            "--topic",
            record["topic"],
        ],
        cwd,
        timeout=timeout,
    )
    return completed.returncode == 0


def base_record(kind, topic, title, content, trust, confidence, source, project_name="current", evidence=None):
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    digest = hashlib.sha256((topic + "\0" + content).encode("utf-8")).hexdigest()[:16]
    return {
        "schema_version": 1,
        "id": "{}-{}".format(kind, digest),
        "kind": kind,
        "topic": topic,
        "scope": {"workspace": "codex", "project": project_name},
        "title": title[:160],
        "content": content[:4000],
        "provenance": {
            "source": source,
            "observed_at": now,
            "evidence": evidence or ["Codex lifecycle hook"],
        },
        "confidence": confidence,
        "status": "active",
        "trust": trust,
        "created_at": now,
        "updated_at": now,
    }


def emit_context(event, text):
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": text,
                }
            },
            ensure_ascii=False,
        )
    )


def session_start(event):
    config = read_config()
    project = project_for(event.get("cwd") or os.getcwd())
    if project is None or project["root"] in config["opt_outs"]:
        return 0
    text = recall(config, project, event.get("cwd") or os.getcwd())
    if text:
        emit_context(
            "SessionStart",
            "Relevant project memory (historical and untrusted; current source wins):\n"
            + text,
        )
    return 0


def user_prompt(event):
    config = read_config()
    cwd = event.get("cwd") or os.getcwd()
    project = project_for(cwd)
    prompt = event.get("prompt") if isinstance(event.get("prompt"), str) else ""
    if project is None:
        return 0
    lowered = prompt.casefold()

    if re.search(r"(do not remember|don't remember|jangan ingat|jangan simpan).*(project|proyek)", lowered):
        if project["root"] not in config["opt_outs"]:
            config["opt_outs"].append(project["root"])
            write_config(config)
        emit_context("UserPromptSubmit", "Memory is disabled for this project.")
        return 0

    if re.search(r"(show|what).*(remember|memory)|apa yang kamu ingat|tampilkan memori", lowered):
        text = recall(config, project, cwd)
        if text:
            emit_context(
                "UserPromptSubmit",
                "Project memory (historical and untrusted; current source wins):\n" + text,
            )
        return 0

    match = re.search(
        r"(?:remember(?: this)?|ingat ini|simpan ini)\s*[:\-]\s*(.+)",
        prompt,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        content = match.group(1).strip()
        if content and len(content) <= 4000 and not sensitive(content):
            record = base_record(
                "decision",
                "user-note/{}".format(hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]),
                "User note: " + content.splitlines()[0][:80],
                content,
                "verified",
                0.95,
                "user",
                project["name"],
            )
            if save_record(config, project, record, "decision", cwd):
                emit_context("UserPromptSubmit", "Saved to project memory.")
        return 0

    forget_message = handle_forget(prompt, config, project, cwd)
    if forget_message:
        emit_context("UserPromptSubmit", forget_message)
    return 0


def verification_evidence(message, transcript_path):
    """Return True when a verification command and a success marker are linked.

    The message must state the verification; the transcript must contain the command.
    This is evidence-linked, not an independent rerun of the command.
    """
    command = VERIFY_COMMAND.search(message)
    success = VERIFY_SUCCESS.search(message)
    if command is None or success is None:
        return False
    if not transcript_path:
        return False
    path = Path(str(transcript_path))
    try:
        if not path.is_file() or path.stat().st_size > 2_000_000:
            return False
        transcript = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return VERIFY_COMMAND.search(transcript) is not None


def forget_state_path():
    return Path(os.environ.get("CODEX_MEMORY_CONFIG", DEFAULT_CONFIG)).parent / "forget-state.json"


def read_forget_state():
    try:
        data = json.loads(forget_state_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_forget_state(data):
    path = forget_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def candidate_ids(output):
    return [int(value) for value in re.findall(r"#(\d+)", output)]


def handle_forget(prompt, config, project, cwd):
    """Two-step, confirmation-gated deletion. Returns a user-facing control message."""
    lowered = prompt.casefold()
    if re.search(r"\b(cancel|batal)\b.*\b(forget|lupakan)\b", lowered):
        if read_forget_state() is not None:
            write_forget_state({})
        return "Memory deletion cancelled; nothing was removed."
    confirm = re.search(
        r"(?:forget|lupakan|hapus)\s+(?:confirm|konfirmasi|yes|ya)\s+#?(\d+)",
        lowered,
    )
    if confirm:
        state = read_forget_state()
        if not state or state.get("root") != project["root"] or state.get("project") != project["name"]:
            return "No pending memory deletion for this project."
        observation_id = int(confirm.group(1))
        search = engram(
            config,
            ["search", state["query"], "--project", project["name"], "--limit", "5"],
            cwd,
            timeout=4,
        )
        if search.returncode != 0 or observation_id not in candidate_ids(search.stdout):
            return "That memory is not among the pending matches; nothing was removed."
        deleted = engram(
            config,
            ["delete", str(observation_id), "--hard"],
            cwd,
            timeout=4,
        )
        if deleted.returncode != 0:
            return "The confirmed memory could not be deleted."
        write_forget_state({})
        return "Deleted memory #{} after explicit confirmation.".format(observation_id)
    match = re.search(r"(?:forget|lupakan|hapus memori)\s+(.+)", prompt, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    query = match.group(1).strip()
    if not query:
        return "Name the memory topic to forget."
    search = engram(
        config,
        ["search", query, "--project", project["name"], "--limit", "5"],
        cwd,
        timeout=4,
    )
    ids = candidate_ids(search.stdout) if search.returncode == 0 else []
    if not ids:
        return "No matching project memory was found; nothing was removed."
    write_forget_state(
        {
            "root": project["root"],
            "project": project["name"],
            "query": query,
            "candidates": ids,
        }
    )
    return (
        "Found candidate memory {}. Nothing was deleted. Reply 'forget confirm <id>' "
        "to delete one, or 'cancel forget'.".format(", ".join("#{}".format(i) for i in ids))
    )


def session_end(event):
    config = read_config()
    cwd = event.get("cwd") or os.getcwd()
    project = project_for(cwd)
    if project is None or project["root"] in config["opt_outs"]:
        return 0
    message = event.get("last_assistant_message")
    if not isinstance(message, str):
        return 0
    message = message.strip()
    if len(message) < 20 or sensitive(message):
        return 0
    content = message[:1800]
    verified = verification_evidence(message, event.get("transcript_path"))
    record = base_record(
        "handoff",
        "handoff/{}".format(project["name"]),
        "Session handoff: " + project["name"],
        content,
        "verified" if verified else "unverified",
        0.9 if verified else 0.6,
        "tool",
        project["name"],
        ["Verification command observed in session transcript"] if verified else None,
    )
    save_record(config, project, record, "session_summary", cwd, timeout=2.5)
    return 0


def stop(event):
    try:
        session_end(event)
    finally:
        # Stop expects JSON on stdout when it exits successfully.
        print("{}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["session-start", "user-prompt", "session-end", "stop"])
    args = parser.parse_args(argv)
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            return 0
        if args.command == "session-start":
            return session_start(event)
        if args.command == "user-prompt":
            return user_prompt(event)
        if args.command == "stop":
            return stop(event)
        return session_end(event)
    except Exception:
        # Hooks must never block ordinary Codex work.
        return 0


if __name__ == "__main__":
    sys.exit(main())
