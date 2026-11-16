"""Preview skill/role installation and the apps/plugins needed to support it.

This command never writes to the target. It is intentionally a preflight, not an
installer. Use package_skill_pack.py for the actual reviewed import.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILL_SOURCE = ROOT / ".agents/skills"
ROLE_SOURCE = ROOT / ".agents/roles"
CHROME_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
)


def which(name):
    return shutil.which(name)


def target_state(target):
    target = Path(target).resolve()
    skills = target / ".agents/skills"
    existing = sorted(path.parent.name for path in skills.glob("*/SKILL.md")) if skills.is_dir() else []
    return {
        "target": str(target),
        "exists": target.is_dir(),
        "skills_dir": skills.is_dir(),
        "existing_skills": existing,
        "has_agents_md": (target / "AGENTS.md").is_file(),
        "has_claude_md": (target / "CLAUDE.md").is_file(),
        "has_engram": (target / ".engram/config.json").is_file(),
        "has_codex_roles": (target / ".codex/agents").is_dir(),
        "has_claude_roles": (target / ".claude/agents").is_dir(),
    }


def requirements(target, with_memory, with_ui):
    state = target_state(target)
    items = []

    def add(name, status, detail, install, required=False):
        items.append({
            "name": name, "status": status, "detail": detail,
            "install": install, "required": required,
        })

    add("Python 3.9+", "ok" if sys.version_info >= (3, 9) else "missing",
        "running {}.{}.{}".format(*sys.version_info[:3]),
        "Install Python 3.9 or newer.", required=True)
    add("Target directory", "ok" if state["exists"] else "missing",
        state["target"], "Create the target directory first.", required=True)
    add("Skill source", "ok" if SKILL_SOURCE.is_dir() else "missing",
        str(SKILL_SOURCE), "Run from the skill-pack repository.", required=True)

    host = []
    for name in ("codex", "claude", "dsh"):
        if which(name):
            host.append(name)
    add("Agent host CLI", "ok" if host else "optional",
        ", ".join(host) if host else "none detected",
        "Install the agent you intend to use; the skill files are portable.", required=False)
    add("Codex wrappers", "ok" if state["has_codex_roles"] else "optional",
        "project .codex/agents" if state["has_codex_roles"] else "not present",
        "Render with scripts/render_agent_adapters.py --host codex --write if desired.", required=False)
    add("Claude wrappers", "ok" if state["has_claude_roles"] else "optional",
        "project .claude/agents" if state["has_claude_roles"] else "not present",
        "Render with scripts/render_agent_adapters.py --host claude --write if desired.", required=False)

    if with_memory or state["has_engram"]:
        engram = which("engram")
        add("Engram memory binary", "ok" if engram else "missing",
            engram or "not found on PATH",
            "Install Engram and run `engram init <project>`; memory is optional.", required=with_memory)
        add("Engram project config", "ok" if state["has_engram"] else "missing",
            str(target / ".engram/config.json"),
            "Run `engram init <project>` in the target; never copy another project's memory.",
            required=with_memory)

    if with_ui:
        chrome = next((path for path in CHROME_PATHS if Path(path).is_file()), None)
        add("Node.js", "ok" if which("node") else "missing", which("node") or "not found",
            "Install Node.js for UI fixture checks; only needed for UI verification.", required=False)
        add("Chrome/Chromium", "ok" if chrome else "missing", chrome or "not found",
            "Install Chrome/Chromium or use another authorized browser runner.", required=False)
        add("Playwright fixture deps", "ok" if (ROOT / "tests/ui/node_modules/playwright-core").is_dir() else "optional",
            "tests/ui node_modules" if (ROOT / "tests/ui/node_modules/playwright-core").is_dir() else "not installed",
            "Run `cd tests/ui && npm install` only for UI fixture checks.", required=False)

    return items


def preview(target, with_roles, with_memory, with_ui):
    state = target_state(target)
    reqs = requirements(target, with_memory, with_ui)
    skills = sorted(path.parent.name for path in SKILL_SOURCE.glob("*/SKILL.md"))
    existing = set(state["existing_skills"])
    conflicts = sorted(existing & set(skills))
    would_import = ["skills ({})".format(len(skills)), "AGENTS.snippet.md"]
    if with_roles:
        roles = sorted(path.stem for path in ROLE_SOURCE.glob("*.yaml") if path.name != "schema.yaml")
        would_import.append("roles ({})".format(len(roles)))
    skipped = []
    if not with_roles:
        skipped.append("roles — opt-in with --with-roles")
    if not with_memory:
        skipped.append("memory runtime — optional; configure a host adapter separately")
    if not with_ui:
        skipped.append("UI fixture dependencies — optional; only for browser checks")
    if not state["has_agents_md"]:
        skipped.append("AGENTS.md — merge AGENTS.snippet.md after import")
    if not state["has_claude_md"]:
        skipped.append("CLAUDE.md — host-specific instructions are not generated")
    missing_required = [item["name"] for item in reqs if item["required"] and item["status"] != "ok"]
    return {
        "mode": "preview-only",
        "target": state["target"],
        "would_import": would_import,
        "conflicts": conflicts,
        "skipped": skipped,
        "requirements": reqs,
        "secrets": "never imported — credentials, .env, API keys, and Authorization headers are excluded",
        "missing_required": missing_required,
        "summary": {
            "would_import": len(would_import),
            "conflicts": len(conflicts),
            "skipped": len(skipped),
            "required_missing": len(missing_required),
        },
    }


def render(report):
    lines = [
        "Agent / Skill Setup Preview",
        "===========================",
        "Target: {}".format(report["target"]),
        "Mode:   preview only — no files are modified",
        "",
        "Would import:",
    ]
    lines += ["  + {}".format(item) for item in report["would_import"]]
    lines += ["", "Conflicts (import backs up before replacing):"]
    lines += ["  ! {}".format(item) for item in report["conflicts"]] or ["  (none)"]
    lines += ["", "Skipped / optional:"]
    lines += ["  - {}".format(item) for item in report["skipped"]] or ["  (none)"]
    lines += ["", "Support requirements:"]
    for item in report["requirements"]:
        mark = {"ok": "+", "missing": "x", "optional": "?"}.get(item["status"], "?")
        lines.append("  {} {} — {}".format(mark, item["name"], item["detail"]))
        if item["status"] == "missing":
            lines.append("      install/action: {}".format(item["install"]))
    lines += ["", "Secrets: {}".format(report["secrets"]), "",
              "Summary: {} would import, {} conflict(s), {} skipped, {} required missing".format(
                  report["summary"]["would_import"], report["summary"]["conflicts"],
                  report["summary"]["skipped"], report["summary"]["required_missing"]),
              "",
              "Next: review this preview, then run package_skill_pack.py import without --apply for the exact file plan."]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=Path.cwd())
    parser.add_argument("--with-roles", action="store_true")
    parser.add_argument("--with-memory", action="store_true")
    parser.add_argument("--with-ui", action="store_true")
    parser.add_argument("--strict", action="store_true", help="exit nonzero when a requested requirement is missing")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = preview(args.target, args.with_roles, args.with_memory, args.with_ui)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render(report))
    if args.strict and report["missing_required"]:
        print("Missing required support: " + ", ".join(report["missing_required"]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
