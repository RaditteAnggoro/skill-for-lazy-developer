# Hermes evolution implementation report

Date: 2026-11-16  
Repository baseline: `938a4af` (17 skills, 213 baseline tests).  
Status: repository-scoped implementation complete; host role dispatch and live model
benchmarks remain explicitly unverified. Changes are in the working tree and are not
committed by this implementation.

## Phase results

| Phase | Delivered | Result |
| --- | --- | --- |
| 0 — baseline | [baseline record](HERMES_BASELINE_20261116.md) | 17 skills; 213 baseline tests passed |
| 1 — quality | Exploratory UI QA, risk-weighted TDD, review/simplification, API diagnosis, spikes, grounded evidence, document actions | References linked; 10-case use-vs-overuse gate passes |
| 2 — roles | Four read-only YAML contracts, schema/validator, deterministic Codex TOML and Claude Markdown wrappers, opt-in pack roles | 4 roles valid; 4+4 wrappers deterministic and parseable; collision rollback tested |
| 3 — delegation | Selective delegation policy, eight-case decision table, labelled simulated trace, fallback states, DSH single-agent rubric | 8/8 cases pass; `live_dispatch: false` |
| 4 — learning | Proposal schema, local staging, secret/PII/injection/duplicate/unobserved-evidence rejection, no active-skill write | [5/5 cases pass](PHASE4_EVIDENCE.md); staging preserves active skills |
| 5 — advanced | API layers, spike contract, document actions, AST dry-run policy, grounded ledger, bounded fan-out policy; qmd/evolver/humanizer deferred | [12 contract cases and 48-ID matrix](PHASE5_EVIDENCE.md) |
| 6 — cross-host | Role docs, host status, DSH fallback, packaging, 48-case evidence matrix | [Wrappers parse](PHASE6_EVIDENCE.md); dispatch NOT_RUN/AUTH_REQUIRED/UNSUPPORTED |

## Commands and observed results

```text
.venv/bin/python scripts/validate_skills.py
→ Validated 17 skills, UI metadata, GitHub YAML, and local links.

.venv/bin/python scripts/validate_roles.py
→ Validated 4 role contract(s).

.venv/bin/python scripts/render_agent_adapters.py --host codex --check
→ 4 codex wrapper(s) are deterministic and current.

.venv/bin/python scripts/render_agent_adapters.py --host claude --check
→ 4 claude wrapper(s) are deterministic and current.

.venv/bin/python scripts/evaluate_delegation.py
→ 8/8 cases pass.

.venv/bin/python scripts/validate_phase_plan.py --json
→ 4/4 phase plans valid.

.venv/bin/python scripts/run_phase6_evals.py
→ Phase 6: 8/8 cases passed.

.venv/bin/python -m unittest discover -s tests -q
→ Ran 258 tests in 9.537s; OK.

.venv/bin/python scripts/build_release.py
→ Built codex-developer-skills-0.1.0.zip (294 files); checksum valid.
```

The existing token benchmark still reports its recorded **63.17% median context
retention reduction** with its stated limitation: it is not a live model-answer or
cost benchmark. Existing routing/trial outputs include blocked model sandbox preflights;
they are not counted as passes.

## Humanized voice

`adaptive-workflow` now uses a casual, Threads-style friend voice when the user is casual:
short reactions, contractions, natural Indonesian particles, light slang, and
code-switching. Slang is never forced; formal users get formal language; safety,
financial, and security warnings drop the jokes. `AGENTS.snippet.md` stays at 640 words.

## Host status

| Host | Observed locally | Evidence level | Status |
| --- | --- | --- | --- |
| Codex CLI 0.167.0 | logged in | STATIC/REPOSITORY_INTEGRATION | TOML wrappers parse; custom role dispatch **NOT_RUN** |
| Claude Code 2.1.322 | installed, `loggedIn: false` | STATIC | Markdown wrappers parse; live dispatch **AUTH_REQUIRED** |
| DSH | adapter target | STATIC | no verified subagent API; **UNSUPPORTED**, use single-agent role-guided rubric |
| Hermes | not required | — | no runtime dependency |

No user-home role installation, global settings change, commit, push, deployment, or
production database operation was performed.

## Evidence matrix

[tests/hermes_spec_matrix.yaml](../tests/hermes_spec_matrix.yaml) accounts for all 48
specification test IDs. It labels STATIC, SIMULATED, REPOSITORY_INTEGRATION, and
NOT_RUN/BLOCKED/DEFERRED evidence separately. A NOT_RUN result is never reported as a
pass.

## Key files

- Role contracts/schema: [`.agents/roles/`](../.agents/roles/)
- Role validator: [scripts/validate_roles.py](../scripts/validate_roles.py)
- Deterministic renderer: [scripts/render_agent_adapters.py](../scripts/render_agent_adapters.py)
- Delegation policy: [adaptive references](../.agents/skills/adaptive-workflow/references/delegation-policy.md)
- Learning proposal tool: [scripts/propose_skill_learning.py](../scripts/propose_skill_learning.py)
- 48-case evidence matrix: [tests/hermes_spec_matrix.yaml](../tests/hermes_spec_matrix.yaml)
- Setup/import preview: [scripts/agent_setup_preview.py](../scripts/agent_setup_preview.py)
- Host status: [tests/host_integration_status.yaml](../tests/host_integration_status.yaml)
- Optional role pack: `python scripts/package_skill_pack.py export --output dist/skill-pack.zip --with-roles`
- Wrappers: [`.codex/agents/`](../.codex/agents/) and [`.claude/agents/`](../.claude/agents/)

## Phase evidence

- [Phase 1 evidence](PHASE1_HERMES_EVIDENCE.md)
- [Phase 2–3 evidence](PHASE2_3_EVIDENCE.md)
- [Phase 4 evidence](PHASE4_EVIDENCE.md)
- [Phase 5 evidence](PHASE5_EVIDENCE.md)
- [Phase 6 evidence](PHASE6_EVIDENCE.md)

## Limitations and deferred work

- No real Codex/Claude/DSH role dispatch was executed; wrappers are static-validated.
- No live model benchmark compares baseline versus candidate for this work. The
  existing routing baseline is recorded separately and is not an A/B result.
- No real browser/DB payment journey was executed; real payment environments remain
  BLOCKED.
- `qmd`/local index, `darwinian-evolver`, and humanizer/style injection remain deferred.
- Role contracts are policy metadata, not sandboxes. Host permissions must be verified.
- No automatic skill-learning promotion exists; a human must review and apply a normal
  repository diff.
- The portable pack's optional roles are opt-in (`--with-roles`); default pack behavior
  is unchanged.
