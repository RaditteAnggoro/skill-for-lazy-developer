# 09 — Capability application review

This matrix records how each of the 17 Lazy Developer skills applies the selected
capabilities from the [upstream comparison](03_EXACT_SKILL_COMPARISON.md). The audit
distinguishes instructions, executable repository tooling, tested fixtures, and
observed host behavior. External integrations retain their own security and license
boundary. Current observation applies to the listed evidence and environment.

| Skill | Capability applied | Evidence and remaining boundary |
| --- | --- | --- |
| `adaptive-workflow` | Outcome-based routing, phase boundaries, native-first tools, and proportional delegation. | [Routing corpus](../../tests/routing_cases.yaml) and [isolated routing results](05_BENCHMARK_RESULTS.md). Role dispatch permissions remain host-specific. |
| `lean-senior-engineering` | Reuse-first decisions, risk-sensitive TDD, focused changes and simplification. | [Engineering workflow](../../.agents/skills/lean-senior-engineering/SKILL.md) and [optional review guidance](../../.agents/skills/lean-senior-engineering/references/review-and-simplify.md). Broad comparative implementation quality remains unmeasured. |
| `systematic-debugging` | Reproduction, cause isolation, and checks that discriminate between hypotheses. | [Diagnosis workflow](../../.agents/skills/systematic-debugging/SKILL.md) and [diagnose-only routing case](../../tests/routing_cases.yaml). Root-cause accuracy requires a separate task grader. |
| `verification-before-completion` | Claim-to-check matching, freshness and explicit handling of skips and blockers. | [Policy](../../.agents/skills/verification-before-completion/SKILL.md) and [receipt tests](../../tests/test_phase_receipts.py). Receipt author and host provenance are still trust boundaries. |
| `research-plan-implement` | Phase plans, resumable handoff, dependency order and input/artifact consistency. | [Plan cases](../../tests/orchestration_cases.yaml) and [local receipt verifier](../../scripts/verify_phase_receipts.py). The agent evaluates evidence within host permissions. |
| `feature-discovery` | Consequential questions, source discovery, testable acceptance and scoped spikes. | [Discovery workflow](../../.agents/skills/feature-discovery/SKILL.md) and [routing corpus](../../tests/routing_cases.yaml). Product decisions remain with the user. |
| `architecture-map` | Source-backed navigation and dependency explanations with optional symbol search. | [Architecture workflow](../../.agents/skills/architecture-map/SKILL.md) and [synthetic impact tests](../../tests/test_impact_evals.py). Graph engines and dynamic-edge coverage need separate evidence. |
| `release-readiness` | Compatibility, configuration, smoke checks, release blockers and rollback. | [Release workflow](../../.agents/skills/release-readiness/SKILL.md), [package workflow tests](../../tests/test_phase7.py), and [source packaging checks](../../tests/test_packaging.py). Environment-specific deployment is separate. |
| `browser-journey-testing` | Real-browser journey observations with outcomes, recovery, keyboard and responsive coverage. | [Browser fixture runners](../../tests/ui/README.md). Coverage uses a synthetic approval scenario across three stacks. |
| `browser-diagnostics` | Reproduction using available browser console, DOM and network evidence. | [Browser diagnostics workflow](../../.agents/skills/browser-diagnostics/SKILL.md), [tool reference](../../.agents/skills/adaptive-workflow/references/tool-selection.md), and fixture page-error handling. Remote DevTools capability requires a scoped connection. |
| `ui-design-intelligence` | Existing tokens and user-job hierarchy, plus enterprise design and adversarial UX review. | [Design workflow](../../.agents/skills/ui-design-intelligence/SKILL.md). Human comparative quality review remains a separate test. |
| `ui-implementation` | Responsive, keyboard-accessible interactions and empty, loading, error and recovery states. | [UI implementation workflow](../../.agents/skills/ui-implementation/SKILL.md) and [build/browser fixtures](../../tests/ui/README.md). Results are limited to the exercised states and widths. |
| `ui-quality-verification` | Targeted visual, keyboard, responsive and exploratory review. | [Quality workflow](../../.agents/skills/ui-quality-verification/SKILL.md) and [UI mode definitions](../../tests/ui/README.md). Structural mode captures screenshots without pixel-baseline comparison. |
| `domain-modeling` | Shared terminology, lifecycle, ownership and testable invariants. | [Domain workflow](../../.agents/skills/domain-modeling/SKILL.md) and [valid/invalid model checks](../../scripts/run_phase6_evals.py). The checks validate the declared model. |
| `spec-to-code-verification` | Requirement IDs, named assertions and recorded outcomes. | [Traceability verifier](../../scripts/verify_spec_traceability.py) and [JUnit coverage tests](../../tests/test_spec_execution.py). Test owners confirm assertion intent and report revision. |
| `skill-security-guard` | Quarantine, defensive source inspection, permission and data-flow review. | [Skill guard](../../.agents/skills/skill-security-guard/SKILL.md) and [scanner boundary tests](../../tests/test_security_scan_boundaries.py). Heuristics leave an explicit manual adoption decision. |
| `transaction-safe-engineering` | Idempotency, replay, concurrency and reconciliation as explicit invariants. | [Transaction workflow](../../.agents/skills/transaction-safe-engineering/SKILL.md), [declaration checks](../../scripts/check_transaction_safety.py), and [synthetic replay behavior](../../tests/test_enhancement_fixtures.py). No live financial, Oracle or Spring Batch execution is claimed. |

The follow-up closes the reference-only traceability gap with an optional JUnit
execution mode. The existing mode says that its evidence is reference lint.
Skipped, failed and missing mapped testcases stop the execution mode from passing.
The synthetic Next.js fixture was updated to 16.4.6 and the React fixture to Vite
7.3.8 after reviewing both lockfiles. npm reported zero known findings for these
updated fixture locks at the time of the audit. Historical baseline results retain
their original fixture versions.

An isolated React approval pilot checked a real browser run from the updated Vite
fixture. The browser report supplied three observations for two requirements: the
success message, the selected row's state change, and cleared selection. Converting
those observed test outcomes to JUnit yielded **2/2 mapped requirements passing**.
The phase verifier accepted the resulting receipts and marked the final phase stale
after an edit to the local spec. This pilot uses the fixture state and actual browser
output. It does not establish persistence, authorization or visual equivalence.

See the [remaining roadmap](07_REMAINING_ROADMAP.md) for cross-upstream task benchmarks,
live dispatch, human UX assessment, and optional integrations with unverified runtime behavior.
The [follow-up comparison](10_PARITY_FOLLOWUP.md) adds source-edge and repayment
results, stronger runtime evidence checks and expanded approval journeys.
