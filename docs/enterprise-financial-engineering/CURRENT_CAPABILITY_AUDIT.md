# Current capability audit

Baseline `66b12c368364ee5ae78add552ad87ac349248a11`. The audit compares that
revision with the requested financial behavior. The delivery report records the
candidate separately. All fixtures use synthetic records.

| Baseline status | Capability | Source and evidence |
| --- | --- | --- |
| Implemented and tested | Risk-based routing, optional specialist review, and scope boundaries | [Adaptive workflow](../../.agents/skills/adaptive-workflow/SKILL.md), [financial reviewer](../../.agents/roles/ld-financial-integrity-reviewer.yaml), and [routing cases](../../tests/routing_cases.yaml). Dispatch evidence from the earlier P2 run covers the explorer role. |
| Implemented and tested | Transaction vocabulary, requirement traceability, and exact local evidence | [Domain modeling](../../.agents/skills/domain-modeling/SKILL.md), [spec verification](../../.agents/skills/spec-to-code-verification/SKILL.md), [JUnit traceability](../../scripts/verify_spec_traceability.py), and [phase receipts](../../scripts/verify_phase_receipts.py). Their passing checks prove the declared scope only. |
| Implemented and tested | Synthetic SQLite replay, balance, and process recovery | [Batch worker](../../tests/enhancement/fixtures/repayment_batch.py), [holdout](../../tests/enhancement/fixtures/repayment_holdout.py), and [restart test](../../tests/test_repayment_batch.py). The earlier million-event result applies to SQLite. |
| Documented | Debugging, source call paths, focused implementation and release checks | [Debugging](../../.agents/skills/systematic-debugging/SKILL.md), [architecture map](../../.agents/skills/architecture-map/SKILL.md), [engineering](../../.agents/skills/lean-senior-engineering/SKILL.md), and [release readiness](../../.agents/skills/release-readiness/SKILL.md). Existing static callsite evidence does not verify Spring proxy or database behavior. |
| Partial | Transaction analysis and Java repayment fixture | [YAML checker](../../scripts/check_transaction_safety.py) originally checked declarations. [Java fixture](../../tests/enhancement/fixtures/java-repayment/README.md) exercised a simplified implementation without a real Spring JobRepository. |
| Partial | Context selection and memory | [Context optimizer](../../scripts/context_optimizer.py), [Codex runtime](../../integrations/codex/memory_runtime.py), and [DSH adapter](../../integrations/dsh/companion-memory/index.js). Provider adapters apply their own project scope. Baseline context selection had no financial reference selector. |
| Missing | Real Spring Batch JDBC restart, PostgreSQL claim/concurrency fixture, Oracle dialect example, executable ledger audit, and Java/SQL source checks | The [earlier benchmark worklist](../upstream-benchmark/05_BENCHMARK_RESULTS.md) separated these gaps from SQLite and instruction-based evidence. |

The existing transaction skill already owns the financial intent, ledger replay and
recovery. The existing financial reviewer covers read-only reconciliation review.
The extension uses these owners and keeps the 17 public skills and four roles.
