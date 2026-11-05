"""Heuristic security triage for an untrusted skill directory.

This is a review aid. A clean result is not proof that an instruction bundle is safe.
"""

import argparse
import json
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
                    "excerpt": line.strip()[:180],
                })
    return findings


def scan_path(path):
    target = Path(path)
    if not target.exists():
        raise ValueError("path does not exist: {}".format(target))
    files = [target] if target.is_file() else [
        item for item in target.rglob("*")
        if item.is_file() and item.suffix.lower() in TEXT_SUFFIXES
    ]
    findings = []
    for file in sorted(files):
        try:
            text = file.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            findings.append({
                "file": str(file), "line": 0, "rule": "read-error",
                "severity": "medium", "excerpt": str(exc),
            })
            continue
        findings.extend(scan_text(text, str(file)))
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
    result = {"path": str(args.path), "verdict": verdict(findings), "findings": findings}
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("verdict: {} ({} finding(s))".format(result["verdict"], len(findings)))
        for item in findings:
            print("{}:{} [{}] {}: {}".format(item["file"], item["line"], item["severity"], item["rule"], item["excerpt"]))
    return 1 if any(item["severity"] == "high" for item in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
