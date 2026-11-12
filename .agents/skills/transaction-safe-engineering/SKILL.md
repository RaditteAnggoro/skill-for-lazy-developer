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

For multi-step operations, use a transaction where the storage supports it; otherwise
use a durable state machine with explicit pending, committed, failed, and compensating
states. Separate external side effects from the local commit. Do not claim atomicity
across systems that cannot provide it.

For batches, persist checkpoints and a replay marker. Replays must be idempotent and
must not reset missing values to zero. Reconcile totals before and after recovery.

## Verify

If live database evidence is necessary, follow the database safeguards in the shared [tool selection guide](../adaptive-workflow/references/tool-selection.md); never assume a connection or treat a client read-only flag as a security boundary.

Test duplicate requests, timeout-after-commit, crash-before-commit, concurrent writers,
partial batch failure, replay, and rollback/compensation. Verify ledger totals and audit
records, not just HTTP 200. Record the actual failure injection and remaining gaps.

If the request is a review, report findings and do not change production behavior without
authorization. Pair with `systematic-debugging` for an unexplained failure and
`spec-to-code-verification` for requirement evidence.
