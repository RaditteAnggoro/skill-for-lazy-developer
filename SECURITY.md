# Security

Skill instructions influence an agent's decisions. Review changes before using them with a sensitive repository, and grant tools only the access needed for the task.

## Reporting a vulnerability

Do not put credentials, private source, or exploitable sensitive details in a public issue. If the hosting repository offers GitHub's private vulnerability reporting, use **Security → Advisories → Report a vulnerability**. Otherwise, contact a repository administrator through an existing private channel and arrange a safe way to share the report.

Include the affected skill/tool version, a minimal sanitized reproduction, expected boundary, actual behaviour, and impact. No maintainer contact address or response-time commitment is established by this template.

## Scope

Reports about unintended tool use, data exposure, filesystem access in repository scripts, or instructions that expand a user's request are useful. The validator checks structure and local links; it is not a security audit of agent behaviour. Browser access and external integrations keep their own permissions and data-handling rules.

## Third-party skills

Use `python scripts/scan_skill_security.py <path>` as a triage aid before adopting a
third-party skill. It looks for prompt overrides, remote-shell installers, credential
patterns, destructive commands, approval or sandbox bypass, exfiltration endpoints,
encoded execution, and unpinned installs. A clean scan is not proof of safety.
Review scripts, hooks, MCP servers, requested permissions, network destinations, and
the uninstall path manually. Do not install or enable a candidate as part of the review.

## DSH memory bundle

The optional bundle under `integrations/dsh/companion-memory` runs Host code and
starts an Engram MCP process. Installing it requires DSH's approval or Full access;
review the bundle before installation. Its guard rejects common credential patterns,
customer email addresses, oversized writes, and raw prompt capture before calling
Engram, but it is pattern-based and is not a complete data-loss-prevention system.
Engram may still retain data in its database, exports, backups, or logs. Do not use
this bundle with a memory store you are not prepared to inspect and delete.

## Codex lifecycle hooks

The Codex adapter installs user-level `SessionStart`, `UserPromptSubmit`, and `Stop`
hooks. Installation does not trust them; review the exact definitions in Codex
`/hooks` before enabling them. The hooks can read project memory and write a bounded
handoff to Engram. They reject obvious credentials and raw prompt capture, but the
runtime is not a complete DLP system. A missing provider must fail open.

## Claude Code lifecycle hooks

The Claude adapter writes command hooks to the user-level `~/.claude/settings.json`.
Review those commands before enabling them. The hooks can read project memory and
write a bounded, unverified handoff to Engram. The installer backs up settings and
removes only its own handlers; it is not a security boundary against a compromised
Claude profile.
