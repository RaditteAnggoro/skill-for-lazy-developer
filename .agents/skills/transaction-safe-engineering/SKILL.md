---
name: transaction-safe-engineering
description: "Review or implement money movement, ledger updates, batch replay, reconciliation, and retry paths for idempotency, atomicity, concurrency, and recoverability. Use only when transaction integrity is at risk; skip projects without financial or equivalent state-transition risk."
---

# Transaction-Safe Engineering

Protect correctness when an operation can move money, change a ledger, or partially
commit durable state. Load this skill only for a demonstrated transaction-integrity
concern; it is not a default for ordinary code changes.

## Model the transaction

Identify the business transaction, owning service, durable writes, external calls, and
the commit boundary. Determine whether the operation is money movement, ledger posting,
inventory reservation, batch replay, reconciliation, or another state transition with
real-world consequence.

State the invariants before changing code:

- exactly-once effect or explicitly bounded at-least-once behavior;
- no double debit/credit, double refund, or duplicate batch application;
- balanced totals and preserved currency/rounding rules;
- no partial commit without a recovery path;
- authorization and approval for high-impact actions;
- audit evidence for every state change.

## Design the safety controls

Use an idempotency key derived from the business operation, not a random retry token.
Persist it with the operation result before returning success. Make retries reuse the
key and return the original result. Define concurrency control for competing writers.
Bind the key to the business payload. A retry with different immutable values is a
conflict. Use storage-enforced uniqueness or an equivalent atomic claim instead of
relying on a sequential read-before-write. Commit the claim and durable effect together.

For multi-step operations, use a transaction where the storage supports it; otherwise
use a durable state machine with explicit pending, committed, failed, and compensating
states. Separate external side effects from the local commit. Do not claim atomicity
across systems that cannot provide it.

For batches, persist checkpoints and a replay marker. Replays must be idempotent and
must not reset missing values to zero. Reconcile totals before and after recovery.

## Select enterprise guidance

Load only the reference required by the observed risk:

- [Spring Batch safety](references/spring-batch-safety.md) for job identity, chunk boundaries, and reader restart.
- [Staging and posting](references/staging-posting-pipeline.md) for ownership, reclaim, posting and dialect examples.
- [Ledger invariants](references/ledger-invariants.sql) for close-out assertions on the documented fixture schema.
- [SQL performance and change safety](references/sql-performance-and-change-safety.md) for plans, migrations and audit evidence.

Where available, use explicit Java/SQL source checks to identify candidates, then
verify the real call proxy, schema, transaction manager and durable outcomes.

For a high-consequence financial change, consider one independent read-only integrity
review of idempotency, replay, transaction boundaries, ledger balance, and auditability.
It is advisory and must not write production data. Do not delegate every transaction
change by default.

## Verify

If live database evidence is necessary, follow the database safeguards in the shared [tool selection guide](../adaptive-workflow/references/tool-selection.md); never assume a connection or treat a client read-only flag as a security boundary.

Test duplicate requests, timeout-after-commit, crash-before-commit, concurrent writers,
partial batch failure, replay, and rollback/compensation. Verify ledger totals and audit
records, not just HTTP 200. Record the actual failure injection and remaining gaps.
For local fixtures, synchronize two writers, reopen the store after a successful
commit, and inject a failure between durable writes. Assert that a failed attempt
leaves no partial effect, a valid retry can finish, and a conflicting replay cannot
change the committed result.

If the request is a review, report findings and do not change production behavior without
authorization. Pair with `systematic-debugging` for an unexplained failure and
`spec-to-code-verification` for requirement evidence.
