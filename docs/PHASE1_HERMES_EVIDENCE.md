# Phase 1 evidence — quality enhancements without delegation

Scope: exploratory UI QA, risk-weighted TDD, pre-commit review, simplification,
grounded evidence, spikes, API-layer diagnosis, and AST dry-run policy. No new skill
was added; the count remains 17.

## Deterministic use-vs-overuse gate

`scripts/evaluate_phase1_enhancements.py` applies an enhancement only when the task
profile justifies it. The ten synthetic cases show:

| Task | Applied | Not applied |
| --- | --- | --- |
| One-line copy | none | exploratory QA, TDD, review, spike |
| Financial retry | TDD, review | exploratory QA, AST |
| Exploratory UI journey | exploratory QA | TDD, evidence ledger |
| Requirement mapping | evidence ledger | TDD, exploratory QA |
| Simple explanation | none | all ceremony |
| API 401 | API-layer diagnosis | exploratory QA |
| Structural search | AST dry-run | TDD |
| Uncertain rendering | spike | review |
| Substantial code review | review, simplify | exploratory QA |
| Docs typo | none | all ceremony |

This is a deterministic policy fixture, not a live model or browser evaluation.

## Preserved routing

The existing routing corpus and policy tests remain green; the `adaptive-workflow`
remains the single router and keeps one primary plus at most two support skills per
phase. No new skill identity was introduced.

## References added

See the linked files under the existing skills; no duplicate skill was created. The
new references are loaded only when their trigger applies.
