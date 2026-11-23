# PostgreSQL and Oracle comparison

| Area | PostgreSQL 18 | Oracle Database 19c reference |
| --- | --- | --- |
| Claim | Ordered candidate CTE with `LIMIT` and `FOR UPDATE SKIP LOCKED`, followed by atomic update. Use explicit ordering when consuming `RETURNING`. | Bounded ordered nonlocking key scan, then top-level singleton `FOR UPDATE SKIP LOCKED` probes. Recheck rows and close cursors. The row-limiting clause has restrictions with `FOR UPDATE`. |
| Indexes | Partial ready and expiry indexes. Primary key and batch/currency/state index. | Explicit `(state, event_key)`, `(state, lease_until, event_key)` and batch/currency/state indexes. Verify cursor and actual plans on the target version. |
| Recovery | Lock expired claims in a bounded transaction. Advance the token and inspect unexpected existing journals. | Apply the same state and version checks with `SYSTIMESTAMP` and Oracle intervals. Use bounded key scans and check each update's row count. |
| Duplicate handling | Single key, same payload and fenced row lock. A unique constraint guards alternate writers. Conflict handling at `READ COMMITTED` may need a subsequent statement to observe the winner. | Use a unique constraint and protected lookup with a new transaction for winner recovery when required. A `MERGE` alone does not prove matching payload or concurrent effects. |
| Runtime measurements | Real embedded PostgreSQL 18.3, PostgreSQL JDBC, concurrent locks and `EXPLAIN (ANALYZE, BUFFERS)` over disposable data. | **NOT_RUN**. SQL and concurrency assumptions reviewed against Oracle documentation. Validate ORA-00060, cursor fetch size, lease timing, plans and commit behavior on the target edition/version. |
| DDL | Some DDL is transactional. Concurrent index operations have special bounds and failure cleanup. | DDL can commit implicitly. Rehearse forward recovery and verify actual locks and online-operation support. |

Both claim algorithms treat a zero-row result as an observation of one attempt.
They do not prove the whole queue is empty. Pause or back off under contention,
track starvation, and still reconcile eligible work before closing the batch.

Examples [PostgreSQL fixture](../../.agents/skills/transaction-safe-engineering/references/postgresql-claim-and-post.sql)
and [Oracle reference](../../.agents/skills/transaction-safe-engineering/references/oracle-claim-and-post.sql).
Primary documentation [PostgreSQL SELECT](https://www.postgresql.org/docs/18/sql-select.html),
[isolation](https://www.postgresql.org/docs/18/transaction-iso.html),
[Oracle SELECT](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/SELECT.html),
and [Oracle transaction processing](https://docs.oracle.com/en/database/oracle/oracle-database/19/lnpls/transaction-processing-and-control.html).
