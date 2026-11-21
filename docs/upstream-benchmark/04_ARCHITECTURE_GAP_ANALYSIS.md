# 04 — Architecture and confirmed gaps

The improvement target is a lightweight chain from user intent to a verified outcome. Routing chooses a workflow, tools provide observations, and host permissions define what can be done. Keep the boundaries separate. Adopt an optional dependency only when measured evidence beats a native fallback and the scope, data handling and rollback are understood.

## Ten significant gaps at the frozen baseline

| # | Area | Confirmed source observation | Effect and action |
| --- | --- | --- | --- |
| 1 | Orchestration | [Simulator](../../scripts/simulate_phase_orchestration.py#L21) copies planned evidence into completed rows. | Keep simulation distinct. The new local verifier derives phase status from current inputs and recorded checks. |
| 2 | Seamless UX | [Phase validator](../../scripts/validate_phase_plan.py#L57) only needs nonempty evidence text. | A structurally valid phase has no observable exit guarantee. Add opt-in required checks and a hold when prerequisites are stale. |
| 3 | Security and privacy | In the [baseline scanner](https://github.com/RaditteAnggoro/skill-for-lazy-developer/blob/69b93d53fa1715a613299204500eb024d170c1a2/scripts/scan_skill_security.py#L29), findings contain raw excerpt text and scans have no explicit symlink or text-size coverage status. | Separate scan boundary from adoption result. Omit excerpts and surface files that need manual review. |
| 4 | Benchmark reliability | The [baseline comparator](https://github.com/RaditteAnggoro/skill-for-lazy-developer/blob/69b93d53fa1715a613299204500eb024d170c1a2/scripts/compare_enhancement_results.py#L22) reports a blocked-pair total without identifying cases that lack any comparable trial. | Reports can show no regressions with zero comparable outcomes. Add case coverage and per-variant blocked counts. |
| 5 | Engineering intelligence | [Impact scorer](../../scripts/run_impact_evals.py) scores file names from a synthetic project. | It cannot measure symbol anchors, dynamic edges, batch boundaries and SQL call chain quality. Build a source-grounded holdout before adding an index. |
| 6 | Specification verification | [ID lint](../../scripts/verify_spec_traceability.py#L18) matches requirement markers in test text. | A marker proves a reference exists. Pair with assertion IDs and execution evidence to establish behavior. |
| 7 | Agent orchestration | [Delegation evaluator](../../scripts/evaluate_delegation.py#L13) consumes booleans from a fixture. [Host status](../../tests/host_integration_status.yaml) separates parsing from dispatch. | Treat dispatch and enforced read limits as separate runtime properties and validate per supported host. |
| 8 | Memory and learning | [Learning proposal staging](../../scripts/propose_skill_learning.py#L54) consumes submitter-provided review and test fields. | A content claim cannot substitute for a receipt. Add evidence provenance and immutable reviewed revisions before extending promotion. |
| 9 | UI, browser, and MCP | [UI CI](../../.github/workflows/ui.yml) runs structural checks for one approval domain across stacks. [Tool-selection evaluator](../../scripts/run_tool_selection_eval.py) supplies synthetic capability scenarios. | Meaningful UX needs task breadth and human review. Tool suitability needs actual calls on safe, bounded fixtures. Preserve browser diagnostics and functional journey ownership. |
| 10 | Transaction safety and portable evidence | [Repayment fixture runner](../../scripts/run_repayment_trial.py) uses SQLite. The [Java fixture](../../tests/enhancement/fixtures/java-repayment/README.md) is in memory. | No measured Spring Batch/Oracle/concurrency/performance outcome. Maintain fixture isolation and add dialect-aware batch/reconciliation scenarios before making a scale claim. |

Native search, reusable code, scope-aware ask thresholds and lightweight packaging stay the default. High-risk changes should declare the invariants or user outcomes that justify escalation, rather than increasing the number of skills. For cross-host parity, measure the same behavior under each host's actual permissions. Preserve `unknown`, `blocked`, and `unsupported` where the capability cannot be verified.

## Priority decisions

- **Adapt** fresh check evidence from the Superpowers and HumanLayer comparison, purpose-based UI critique from Anti-slop, Unslop and Impeccable, and coverage-aware reporting from independent evaluator designs. Keep original implementations and case definitions.
- **Integrate optionally** browser diagnostics and symbol indexing through a capability already present in the host, after a bounded comparison. Leave future Codegraph adapters or Archify rendering opt-in.
- **Reject** a mandatory Hermes runtime, unsafe deployment or browser automation, a persistent default context service, and automatic rule promotion. Those change execution authority, residency or overhead without proving additional value for the normal task.
- **Defer** cross-artifact semantic indexing, Impeccable account/sync, migration to a new memory provider, broad React rule imports, and installing external evaluation runtimes. These require explicit data-flow, dependency, and outcome evidence. [Provenance and boundaries](08_LICENSE_SECURITY_PROVENANCE.md)
