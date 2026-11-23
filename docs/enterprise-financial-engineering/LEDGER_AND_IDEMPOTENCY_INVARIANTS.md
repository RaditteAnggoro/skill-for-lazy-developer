# Ledger and idempotency invariants

The [read-only SQL oracle](../../.agents/skills/transaction-safe-engineering/references/ledger-invariants.sql)
returns an invariant label and reference for each violation. Run it in a stable
reconciliation scope after work quiesces. Use an equivalent scope for the stage and
journal rows. Open or intentionally rejected work must receive its own reports.

| Assertion | Example failure |
| --- | --- |
| One effect per domain key | Competing workers try to create the same journal. A fixture uniqueness constraint and same-key concurrency test check this. |
| Matching immutable payload | A replay supplies a different fingerprint. Preserve the original committed result and reject the alternate inputs. |
| Balanced journal by currency | A changed line, foreign-currency line, missing side, or an extra line fails the relevant oracle. |
| Business effect reconciles once | Accepted staging counts and amounts match distinct journals per batch and currency. Each journal debit and credit is checked separately against the single business effect. |
| Date and adjustment evidence | Check business and value dates against stage. A backdated full reversal uses its own key, references the original, and mirrors account directions. A separately keyed adjustment links to a matching-currency original and has its own amounts and authorization. |
| Traceability | Missing audit record, approver separation, correlation, reason, scope/date mismatch, or outbox row blocks verification. |

Before adopting an idempotency key, define source event and effect identity,
canonical fingerprint fields, serialization and rounding, uniqueness enforcement,
response on conflict, replay lifetime, and observability. Different installment,
value date, or transaction type can mean a separate authorized effect depending on
the domain. Keep effective date and posting date independent. The reference uses
positive minor units, exactly two lines, one currency and a one-time full reversal.
Complex portfolios need additional allocation, FX, balance, and adjustment checks.

The [JUnit fixture](../../tests/enhancement/fixtures/enterprise-batch/src/test/java/fixture/EnterpriseBatchTest.java)
reconciles completed rows and uses corrupt amount, audit and date controls to check
that the oracle detects regressions. It keeps settlement acknowledgement separate
from the successful local posting outcome.
