# Staging, posting and reconciliation

Use these as candidate states. Identify the system that owns each transition and
the durable proof of the transition before adapting the lifecycle.

| Transition | Invariant |
| --- | --- |
| `READY` or `RETRYABLE` → `CLAIMED` | One committed owner, finite lease, and increasing version. Eligible keys are selected in deterministic order within each claim. |
| `CLAIMED` → `POSTED` | Validate owner, lease, token, and immutable payload. Commit the journal, lines, audit, outbox, and stage together. |
| Expired `CLAIMED` → `RETRYABLE` | A bounded recovery transaction locks and rechecks expiry. It advances the version, so a previous worker cannot post. An unexpected existing journal goes to reconciliation. |
| `READY` or `CLAIMED` → `REJECTED` | A clearly classified invalid business item has no journal. Preserve its reason, counts and disposition. |
| `CLAIMED` → `FAILED` | Accounting or infrastructure failure stays visible. Retry after a verified recovery decision. |
| Unknown effect → `RECONCILIATION_REQUIRED` | Stop blind retries. Query the outcome using the original provider correlation or idempotency key. Record discrepancies. |
| Approved correction → `COMPENSATING` → `POSTED` | Create a separately keyed and linked reversal or adjustment with its own effective date and approval. Preserve original evidence. |

Choose unique effect identity according to the domain. A repayment may have a source
event ID, loan, installment, value date and transaction type. Identify which fields
define distinct approved effects, and which must only participate in the canonical
payload fingerprint. Document rounding, locale, precision and field normalization.
A retry with an identical key and fingerprint returns the original result. A different
fingerprint is rejected. A native conflict statement still needs a uniqueness constraint,
transaction boundary and verification of the winning result. Use integer minor units
or exact decimal rules with declared currency scales.

Use a short claim transaction and a separate posting transaction with fencing. Avoid
holding locks during application or network calls. A retry after commit reads the
committed result. Roll back on a failed invariant. If execution stops when the durable
outcome is unknown, reconcile within a new transaction before acting. At-least-once
outbox dispatch uses a stable message key and a receiver that handles duplicates.
Record `UNKNOWN` after an ambiguous timeout, check provider status, and persist a
matched acknowledgement. A local database commit cannot prove external settlement.

## Dialects and verification

- [PostgreSQL fixture](postgresql-claim-and-post.sql) uses a deterministic bounded
  `FOR UPDATE SKIP LOCKED` CTE and atomic update at `READ COMMITTED`. Queue reads
  may skip locked work. A zero-row claim is not a complete inventory of available work.
  Requeue in bounded `(lease_until, event_key)` order. Test competing sessions,
  expired fences, deadlock recovery and commit-response ambiguity.
- [Oracle reference](oracle-claim-and-post.sql) locks each bounded candidate by
  key with an explicit Oracle `SKIP LOCKED` query. Confirm candidate scan limits,
  cursor close and transaction lock lifetime against the target version. Use Oracle
  timestamp and interval semantics. Verify the equivalent outcomes on Oracle.
- Run [ledger checks](ledger-invariants.sql) at a stable closed-batch cut. Compare
  accepted business effects to distinct journals by batch and currency. Compare
  each accounting side independently, and report rejections, outstanding effects,
  reversals and unknown acknowledgements separately.

The SQL assumes a single-currency, two-line journal and a one-time full reversal.
A multi-currency, fee, split-ledger, or partial reversal design needs its own
oracle. Keep correlation, reason codes and decision evidence across all writes.
