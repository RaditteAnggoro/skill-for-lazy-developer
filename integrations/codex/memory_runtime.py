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
import shlex
import subprocess
import sys
import tempfile


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
    r"\b(pytest|python(?:3(?:\.\d+)?)? -m (?:pytest|unittest)|npm test|pnpm test|yarn test|go test|cargo test|"
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


RECORD_ENVELOPE = re.compile(r"<!-- memory-record:v1 (\{.*?\}) -->", re.DOTALL)


def project_fingerprint(project):
    return hashlib.sha256(project['root'].encode('utf-8')).hexdigest()


def provider_project(project):
    return f"ld-{project_fingerprint(project)}"


def recall(config, project, cwd):
    namespace = provider_project(project)
    # The CLI context view abbreviates the body of an envelope. A project-scoped
    # export supplies complete records and is removed before any context is returned.
    with tempfile.TemporaryDirectory(prefix='ld-memory-') as temporary:
        output = Path(temporary) / 'observations.json'
        completed = engram(config, ["export", str(output), "--project", namespace], cwd, timeout=4)
        if completed.returncode != 0 or not output.is_file() or output.stat().st_size > 16 * 1024 * 1024:
            return ""
        try:
            exported = json.loads(output.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            return ""
    observations = exported.get('observations') if isinstance(exported, dict) else None
    if not isinstance(observations, list):
        return ""
    records = []
    for item in observations:
        if (not isinstance(item, dict) or item.get('project') != namespace
                or item.get('scope') != 'project' or not isinstance(item.get('content'), str)):
            continue
        block = item['content'].strip()
        match = RECORD_ENVELOPE.match(block)
        if not match or len(block) > 1800 or sensitive(block):
            continue
        try:
            meta = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        scope = meta.get('scope') if isinstance(meta, dict) else None
        if (scope is None or not isinstance(scope, dict) or scope.get('project') != project['name']
                or meta.get('status') != 'active' or meta.get('project_fingerprint') != project_fingerprint(project)):
            continue
        records.append((str(item.get('updated_at', '')), block))
    selected = []
    size = 0
    for _, block in sorted(records, reverse=True):
        if size + len(block) + 2 > 1800:
            break
        selected.append(block)
        size += len(block) + 2
    return "\n\n".join(reversed(selected))


def envelope(record, project):
    meta = {
        "id": record["id"],
        "kind": record["kind"],
        "topic": record["topic"],
        "status": record["status"],
        "trust": record["trust"],
        "confidence": record["confidence"],
        "scope": record["scope"],
        "project_fingerprint": project_fingerprint(project),
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
            envelope(record, project),
            "--type",
            engram_type,
            "--project",
            provider_project(project),
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

    if project["root"] in config["opt_outs"]:
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


def _transcript_invocations(transcript, turn_id=None):
    """Use typed host events and never infer exit status from command output."""
    calls = {}
    completed = []
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        event_type = event.get('type')
        if event_type == 'event_msg':
            payload = event.get('payload')
            if (not isinstance(payload, dict) or payload.get('type') != 'item_completed'
                    or (turn_id is not None and payload.get('turn_id') != turn_id)):
                continue
            item = payload.get('item')
            if (isinstance(item, dict) and item.get('type') == 'CommandExecution'
                    and item.get('status') in ('completed', 'failed', 'declined')):
                argv = item.get('command')
                if isinstance(argv, list) and argv and all(isinstance(arg, str) for arg in argv):
                    exit_code = item.get('exit_code') if item['status'] == 'completed' else None
                    completed.append((item.get('id'), shlex.join(argv), exit_code))
            continue
        if turn_id is not None:
            continue
        if event_type == 'item.completed':
            item = event.get('item')
            if (isinstance(item, dict) and item.get('type') == 'command_execution'
                    and item.get('status') in ('completed', 'failed')):
                exit_code = item.get('exit_code') if item['status'] == 'completed' else None
                completed.append((item.get('id'), item.get('command'), exit_code))
            continue
        call_id = event.get('call_id')
        if not isinstance(call_id, str) or not call_id:
            continue
        if event_type == 'tool_call':
            calls[call_id] = event.get('command')
        elif event_type == 'tool_result' and call_id in calls:
            completed.append((call_id, calls.pop(call_id), event.get('exit_code')))
    return completed


def _command_text(command):
    try:
        tokens = shlex.split(command)
    except ValueError:
        return command.strip()
    if len(tokens) == 3 and Path(tokens[0]).name in {'sh', 'bash', 'zsh'} and tokens[1] in {'-c', '-lc'}:
        return tokens[2].strip()
    return command.strip()


def verification_evidence(message, transcript_path, turn_id=None):
    """Return linked verification metadata, or None.

    The message must state a verification command and success. The transcript must
    contain the same command with a success/exit result tied to that invocation. This is
    evidence-linked, not an independent rerun of the command.
    """
    command_match = VERIFY_COMMAND.search(message)
    success = VERIFY_SUCCESS.search(message)
    if command_match is None or success is None or not transcript_path:
        return None
    path = Path(str(transcript_path))
    try:
        if not path.is_file() or path.stat().st_size > 2_000_000:
            return None
        transcript = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for call_id, command, exit_code in reversed(_transcript_invocations(transcript, turn_id)):
        if not isinstance(call_id, str) or not isinstance(command, str):
            continue
        exact = _command_text(command)
        kind = VERIFY_COMMAND.match(exact)
        literal = r'(?:^|[\s`])' + re.escape(exact) + (
            r'(?=`|$|[.!](?:\s|$)|\s+(?:passed|succeeded|ok|success|exit(?:ed)?)\b)'
        )
        if kind is None or not re.search(literal, message, re.I):
            continue
        if type(exit_code) is not int or exit_code != 0:
            return None
        fingerprint = hashlib.sha256((call_id + "\0" + command + "\0" + "0").encode()).hexdigest()[:16]
        return {"command": kind.group(0), "exit_status": 0,
                "fingerprint": fingerprint}
    return None


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
    return [int(value) for value in re.findall(r"^\[\d+\] #(\d+) \(", output, re.MULTILINE)]


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
        if not state or state.get("provider_project") != provider_project(project):
            return "No pending memory deletion for this project."
        observation_id = int(confirm.group(1))
        if observation_id not in state.get('candidates', []):
            return "That memory is not among the pending matches; nothing was removed."
        search = engram(
            config,
            ["search", state["query"], "--project", provider_project(project), "--limit", "5"],
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
        ["search", query, "--project", provider_project(project), "--limit", "5"],
        cwd,
        timeout=4,
    )
    ids = candidate_ids(search.stdout) if search.returncode == 0 else []
    if not ids:
        return "No matching project memory was found; nothing was removed."
    write_forget_state(
        {
            "provider_project": provider_project(project),
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
    verified = verification_evidence(message, event.get("transcript_path"), event.get("turn_id"))
    record = base_record(
        "handoff",
        "handoff/{}".format(project["name"]),
        "Session handoff: " + project["name"],
        content,
        "verified" if verified else "unverified",
        0.9 if verified else 0.6,
        "tool",
        project["name"],
        [
            "verification command={} exit_status={} fingerprint={}".format(
                verified["command"], verified["exit_status"], verified["fingerprint"]
            )
        ] if verified else None,
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
