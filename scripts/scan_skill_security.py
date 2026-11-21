"""Heuristic security triage for an untrusted skill directory.

This is a review aid. A clean result is not proof that an instruction bundle is safe.
"""

import argparse
import json
import os
from pathlib import Path
import re
import sys


RULES = [
    ("prompt-override", "high", re.compile(r"\b(ignore|disregard|forget)\b.{0,40}\b(previous|all|system|developer)\b.{0,30}\b(instructions?|prompt|message)\b", re.I)),
    ("system-prompt-access", "high", re.compile(r"\b(system|developer)\s+(prompt|message)\b.{0,30}\b(reveal|print|dump|send|expose)\b", re.I)),
    ("remote-shell", "high", re.compile(r"\b(curl|wget)\b[^\n|]{0,200}\|\s*(ba|z)?sh\b", re.I)),
    ("destructive-root", "high", re.compile(r"\brm\s+-rf\s+/(?:\s|$|\*)", re.I)),
    ("credential-pattern", "high", re.compile(r"(BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})")),
    ("sandbox-bypass", "high", re.compile(r"--dangerously-bypass|sandbox[^\n]{0,30}(disable|off)|full access", re.I)),
    ("approval-bypass", "high", re.compile(r"\b(disable|bypass|skip)\b.{0,30}\bapproval\b|\bnever\s+ask\s+for\s+approval\b", re.I)),
    ("exfiltration-webhook", "high", re.compile(r"https?://(?:discord|hooks\.slack|t\.me|webhook\.site|requestbin)", re.I)),
    ("encoded-exec", "medium", re.compile(r"\b(base64|b64)\b[^\n]{0,80}\b(decode|eval|exec|sh)\b", re.I)),
    ("broad-permissions", "medium", re.compile(r"\bchmod\s+777\b|\bchown\s+root\b|\bsudo\b", re.I)),
    ("unpinned-install", "medium", re.compile(r"\b(pip|npm|pnpm)\s+(install|add)\s+(?!.*(?:==|@|--frozen|--lock))", re.I)),
]
TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json", ".py", ".sh", ".js", ".mjs", ".ts"}
MAX_TEXT_BYTES = 1024 * 1024


def scan_text(text, filename="<input>"):
    findings = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for rule, severity, pattern in RULES:
            match = pattern.search(line)
            if match and re.search(r"\b(do not|never|avoid|don't)\b.{0,80}\b(execute|run|use|allow|install)\b", line[:match.start()], re.I):
                continue
            if match:
                findings.append({
                    "file": filename,
                    "line": line_number,
                    "rule": rule,
                    "severity": severity,
                    "excerpt": "[source text omitted]",
                })
    return findings


def scan_path(path):
    target = Path(path)
    findings = []

    def unscanned(file, rule):
        findings.append({"file": str(file), "line": 0, "rule": rule,
                         "severity": "medium", "excerpt": "[content not scanned]"})

    def scan_file(file):
        if file.is_symlink():
            unscanned(file, "symlink-not-scanned")
            return
        if not file.is_file():
            unscanned(file, "nonregular-not-scanned")
            return
        try:
            with file.open("rb") as stream:
                data = stream.read(MAX_TEXT_BYTES + 1)
            if len(data) > MAX_TEXT_BYTES:
                unscanned(file, "size-limit")
                return
            text = data.decode("utf-8")
            if "\x00" in text:
                unscanned(file, "binary-not-scanned")
                return
        except UnicodeError:
            unscanned(file, "binary-not-scanned")
            return
        except OSError:
            unscanned(file, "read-error")
            return
        findings.extend(scan_text(text, str(file)))

    if target.is_symlink():
        unscanned(target, "symlink-not-scanned")
    elif not target.exists():
        raise ValueError("path does not exist: {}".format(target))
    elif target.is_dir():
        for directory, dirs, files in os.walk(
                target, onerror=lambda exc: unscanned(exc.filename or target, "read-error")):
            root = Path(directory)
            dirs.sort()
            for name in dirs[:]:
                if (root / name).is_symlink():
                    unscanned(root / name, "symlink-not-scanned")
                    dirs.remove(name)
            for name in sorted(files):
                file = root / name
                if file.is_symlink() or file.suffix.lower() in TEXT_SUFFIXES:
                    scan_file(file)
    else:
        scan_file(target)
    return findings


def verdict(findings):
    if any(item["severity"] == "high" for item in findings):
        return "reject"
    if findings:
        return "review"
    return "accept"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        findings = scan_path(args.path)
    except (OSError, ValueError) as exc:
        print("scan failed: {}".format(exc), file=sys.stderr)
        return 2
    result = {"path": str(args.path), "scope": "heuristic_triage",
              "verdict": verdict(findings), "findings": findings}
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("verdict: {} ({} finding(s))".format(result["verdict"], len(findings)))
        for item in findings:
            print("{}:{} [{}] {}: {}".format(item["file"], item["line"], item["severity"], item["rule"], item["excerpt"]))
    return 1 if any(item["severity"] == "high" for item in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
