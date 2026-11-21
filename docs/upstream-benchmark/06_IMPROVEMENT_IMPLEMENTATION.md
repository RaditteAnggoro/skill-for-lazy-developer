# 06 — Local improvement implementation

| Gate | Change | Evidence |
| --- | --- | --- |
| P0 scanner handling | [Scanner](../../scripts/scan_skill_security.py) omits source text, flags links without following them, and limits reads of eligible text files. Existing heuristic verdicts remain compatible. [Guard instructions](../../.agents/skills/skill-security-guard/SKILL.md) define the quarantine assumption. | [Regression tests](../../tests/test_security_scan_boundaries.py), benign scan case, and existing negative scanner fixtures. |
| P0 comparison coverage | [Comparator](../../scripts/compare_enhancement_results.py) rejects an empty or malformed denominator. Output includes scheduled pairs, blocked count by variant, uncovered case IDs, and coverage status. Cases with no comparable pairs exit 3 after writing the diagnostic report. | [Comparison tests](../../tests/test_enhancement_comparison.py) cover uncovered, partially covered, complete and incompatible configurations. |
| P1 phase continuity | [Verifier](../../scripts/verify_phase_receipts.py) checks the exact plan, declared inputs, required observations and artifact digests. Missing receipts lead to `ready`/`waiting`, stale evidence holds dependent phases, and a blocked observation cannot complete a phase. The legacy validator and simulator stay available. | [Tests](../../tests/test_phase_receipts.py) cover positive replay, absent/stale receipts, missing artifact, blocked outcomes, duplicate receipts, and changed plan. [Usage](../../.agents/skills/research-plan-implement/references/phase-receipts.md) describes the opt-in contract. |

The receipt verifier is read-only. It evaluates the supplied record and current files. It does not launch steps or validate the provenance of self-reported check status. Use trusted check observations and name all relevant inputs when filing receipts. Source and artifact hashes bind the interpretation to supplied content. Role isolation, runtime execution and provider permission enforcement remain host responsibilities.

This increment requires no new skill, role or package dependency. Upstream code stays in the separate reference directory and is not part of the package. No automatic hooks, tool activation or global settings were introduced. To roll back the local feature in a consuming project, retain the original skill references and use the previous plan validator. To roll back source changes, reverse only the files in this change while preserving other work.

## Changed paths

- `.agents/skills/research-plan-implement/SKILL.md`, `.agents/skills/research-plan-implement/references/phase-receipts.md`, `.agents/skills/skill-security-guard/SKILL.md`
- `scripts/compare_enhancement_results.py`, `scripts/scan_skill_security.py`, `scripts/verify_phase_receipts.py`, `scripts/run_local_upgrade_controls.py`
- `tests/test_enhancement_comparison.py`, `tests/test_phase_receipts.py`, `tests/test_security_scan_boundaries.py`
- `CHANGELOG.md`, `docs/SOURCES.md`, and [all eight reports plus the source manifest](01_SOURCE_INVENTORY.md#local-components)

## Phase trace

| Phase | Skill | Outcome and evidence |
| --- | --- | --- |
| Freeze baseline and sources | `research-plan-implement` | VERIFIED for baseline revision, source inventory, 24 current commits, and seven historical pins. |
| Review and compare | `skill-security-guard` | PARTIALLY_VERIFIED for static source capability and provenance. Reviewed a sample beyond the README for every source. Runtime and dependency approval were outside this review. |
| Implement local changes | `research-plan-implement` | VERIFIED for five offline controls. The benchmark worklist separates executable local tests from tasks requiring a new environment or reviewed upstream adapter. |
| Final checks | `verification-before-completion` | VERIFIED for 17 skills, four role contracts, all eight rendered wrappers, four phase-plan cases, 277 unit tests and eight Phase 6 fixtures. Browser structural checks passed across plain, React, and a fresh Next build. Local routing A/B was 9/9 on each side. Cross-upstream behavior comparison is INSUFFICIENT_EVIDENCE. |
