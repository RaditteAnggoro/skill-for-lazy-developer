# Changelog

## Unreleased

- Preserve unrelated files during skill-pack rollback and block unsafe legacy rollback.
- Honor DeepSeek project memory opt-out within the current session before recall and handoff.
- Add a Codex compatibility manifest; clarify token-optimizer runtime limitations.

- Complete Phase 7 with a portable skill pack: deterministic export, manifest and
  checksum verification, previewable import, backup, and rollback.
- Reject tampered archives, duplicate members, and path traversal; preserve unrelated
  skills while updating managed skill directories and `AGENTS.snippet.md`.
- Add portable-pack documentation, adapter compatibility coverage, and a reviewed
  development/test license inventory.
- Fix stale Phase 3 documentation and gate wording: handoffs are conditional, forget is
  confirmed, and Claude live verification is deferred rather than a required live check.
- Harden the skill-security scanner against a negation false positive while retaining
  rejection of unsafe install instructions.
- Add Phase 6 engineering intelligence and safety: `domain-modeling`,
  `spec-to-code-verification`, `skill-security-guard`, and optional
  `transaction-safe-engineering`.
- Add deterministic domain, specification-traceability, security-scanning, and
  transaction-safety checkers with eight positive/negative cases.
- Keep third-party skill adoption review-only; the security guard never installs a
  candidate and the optional transaction skill is not implicitly invoked.
- Add Phase 5 UI/UX intelligence: `ui-design-intelligence`, `ui-implementation`, and
  `ui-quality-verification`, with enterprise profiles for tables, filters, approvals,
  long forms, reconciliation, and dense financial data.
- Add plain-web, React/Vite, and Next.js fixtures with six screenshot baselines and
  keyboard, responsive, empty/loading/error, filter, selection, and bulk-approval checks.
- Extend `browser-diagnostics` with an explicit boundary: investigate unexplained
  failures, but hand planned quality audits to `ui-quality-verification`.
- Complete Phase 4 with a context optimizer and token benchmark: 63.17% median context
  reduction across eight cases, all required facts retained, critical constraints copied
  verbatim, and full raw tool/source evidence recoverable.
- Add `tiktoken` measurement with a lexical fallback, a project-scoped selection policy,
  and a repeatable before/after benchmark runner.
- Close Phase 3 with `verified-with-deferred-claude`: Codex has live transcript-backed
  verified handoff and confirmed forget; DSH has live lifecycle and confirmed forget;
  Claude's hook contract is tested and live verification is deferred for credentials.
- Promote handoffs to `verified` only when a verification command and success marker
  are linked to the session transcript; otherwise retain `unverified` at confidence 0.6.
- Replace advisory forget with a two-step, confirmation-gated deletion flow across the
  shared runtime and DSH Host plugin.
- Open Phase 4 as in-progress with explicit token-reduction, correctness,
  critical-constraint, and raw-evidence gates; no optimization result is claimed yet.
- Extend Phase 3 to DSH lifecycle hooks: `agent/created` recall, `agent/pre-step`
  controls, and `agent/turn-stopping` unverified handoff in the companion-memory
  bundle, with fail-open behavior and a Node lifecycle test.
- Add the Claude Code adapter: user-level `settings.json` hook merge, shared memory
  runtime, ordinary-language controls, unverified handoff, fail-open behavior,
  backups, idempotence, uninstall, and rollback.
- Fix DSH recall injection: add a complete message identity and inject during the
  pre-step with the real prompt. Live DSH recall, remember, handoff, opt-out, fail-open,
  and uninstall now pass. Record that Claude has no live binary/auth rather than claiming
  unobserved delivery.
- Open Version 2 Phase 3 with a Codex-first vertical slice: `SessionStart` recall,
  ordinary-language remember/opt-out controls, a bounded `Stop` handoff, fail-open
  behavior, and a reversible user-level hook installer.
- Record a real Codex end-to-end run with Engram: recall, remember, handoff, missing
  provider, opt-out, privacy skip, installer idempotence, rollback, and uninstall all
  passed.
- Keep the Codex handoff explicitly unverified and keep DSH/Claude lifecycle adapters
  as later Phase 3 increments.
- Add a DeepSeek Harness (DSH) adapter: project skill discovery uses the native
  `.agents/skills` roots, the shared instructions are merged with a DSH-specific
  routing calibration, and the installer is idempotent, backed up, checkable, and
  reversible.
- Add a DSH/DeepSeek routing evaluation runner and run the full 24-case corpus,
  including read-only, ambiguity, browser, release, and interaction boundaries.
- Add a DSH memory bundle that connects Engram through `dsh-mcp-client`, exposes the
  Engram tools, fails open when Engram is unavailable, and adds a Host guard that
  blocks sensitive writes before they reach the provider.
- Record standard DSH verification: nine skills, full-corpus routing, memory
  save/search/context/restart/delete, cross-project isolation, a privacy canary,
  provider-failure startup, and bundle install/uninstall.
- Complete Version 2 Phase 2 with a provider-neutral memory record and portable bundle
  contract, lifecycle and supersession checks, evidence-backed provenance, repository
  anchor demotion, and pre-storage rejection of secrets or customer data.
- Add a repeatable local-only memory provider bake-off using disposable data and home
  directories, contract filtering, stale/isolation probes, privacy scans, deletion,
  restart, and portable import checks.
- Record measured ai-memory 3.4.0 and Engram 3.6.2 trials: both met the hard gates;
  Engram is selected for the first Phase 3 runtime adapter because it had lower observed
  setup and query overhead and supports portable import.
- Keep Phase 3 blocked: no lifecycle hook, automatic capture, MCP integration, or
  user-facing memory command is implemented or claimed.
- Complete Version 2 Phase 1 with an approachable, non-corporate companion contract
  that matches conversational register, welcomes basic questions, and remains honest
  about identity, memory, tools, and evidence.
- Add interaction-quality grading for redundant questions, canned/formal language,
  concise continuation, Indonesian conversation, missing context, and safe pushback
  against removing duplicate-payment protection.
- Expand the routing corpus from 20 to 24 cases, avoid redundant debugging and
  implementation chains, and keep targetless requests at the adaptive router.
- Bound the always-on companion policy to 200 words and the complete consuming
  snippet to 640 words while leaving detailed workflows progressively loaded.
- Complete the Version 2 Phase 0 capability baseline without opening Phase 1.
- Add an evidence-gated Version 2 development plan and capability matrix that keep
  memory, context budgeting, tool-output filtering, continuous learning, and agent
  evaluation out of the user-facing skill list.
- Expand the natural-language routing corpus from 13 to 20 direct, contextual, and
  negative-control cases covering every installed workflow as a primary route.
- Add machine-checked phase dependencies, capability ownership, overlap decisions,
  and a reusable ephemeral read-only routing evaluation runner.
- Record a final 20/20 structured routing trial and the fixture corrections that
  preceded it; all later phases remain blocked.
- Add an implicitly invoked adaptive workflow that selects and sequences focused
  skills from natural-language tasks.
- Replace skill-name-first examples and UI prompts with automatic routing,
  outcome-based choices, and a normal-language quick start.
- Add a routing policy, 13-case prompt corpus, policy tests, and an updated automatic
  workflow illustration.
- Add project, third-party, inspiration, and citation notices to the source and
  release archive.
- Add a visual README tour with a workflow illustration, task-routing diagram and expandable prompt walkthroughs.
- Add passive author and project provenance metadata to the README source and distributed documentation.

## 0.1.0 — 2026-10-28

- Eight focused skills covering implementation, debugging, verification, discovery, staged work, architecture, release readiness, and browser diagnostics.
- Optional references for test design, reviews/debt, handoffs, and release checks.
- Consuming-project instruction snippet and trial prompts.
- Source acknowledgements and documented capability limits.
- Structure/link validation, tooling tests, GitHub Actions workflow, and release archive builder.
- Repository maintenance, contribution, security, and publishing documentation.
