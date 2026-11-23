# Spring Batch safety

Use for a financial Spring Batch job or comparable chunk workflow with durable
checkpoints. Identify Spring Batch, Boot, Java, driver, database, transaction
manager and topology from current manifests and configuration. Match APIs and
behavior to those versions. The accompanying fixture uses Batch 5.2, JDBC
metadata and Java 17-compatible source. On Boot, check whether auto-configuration
or an explicit Batch configuration owns the repository, launch behavior and schema.

## Job identity and restart

| Concept | Verify |
| --- | --- |
| Job instance | Job name plus identifying parameters. Name the business date, batch type, and input snapshot/tenant only if they define a distinct eligible execution. |
| Job execution | One attempt for an instance. Keep operator, correlation and operational options non-identifying unless they change the business effect. |
| `FAILED` or `STOPPED` | Resume the same restartable instance with compatible inputs and context. Verify completed steps and restart configuration before running. |
| `ABANDONED` or `COMPLETED` | Apply disposition or an approved reprocessing procedure. Completed instances cannot be restarted. An abandoned job is not a routine restart candidate. |
| Stale `STARTED` | Confirm the original process is gone. Compare durable postings, leases and metadata. Use an authorized operational recovery procedure before retry. |

Use an authorized reprocessing identity only when the business allows a distinct
effect or compensating event. Keep the original business idempotency key when
retrying the same effect. Avoid random identifying parameters and timestamp-based
restart bypasses. Persist instance and execution metadata in a durable
`JobRepository`. Version serialized `ExecutionContext` state, avoid sensitive
fields, and test reading older checkpoints across a compatible rollout.

## Chunk and rollback

Trace `ItemReader` → `ItemProcessor` → `ItemWriter`, the listener order, and the
actual commit boundary. Check that the chunk manager and metadata as well as
business writes enlist as intended. When metadata and postings use distinct
local transactions, identify the possible commit order and reconcile every gap.
A durable, independently deduplicated effect is essential when an atomic boundary
is unavailable. Do not send an external request as a substitute for a local commit.

Process and writer code can see the same input after rollback. The retry policy
needs exception classes, bounded attempts, backoff, and an idempotent writer.
Stateful retry needs a stable item key across transaction re-entry. Stateless retry
is appropriate only where its transaction scope and re-execution behavior are safe.
Test interruption before commit and after commit before acknowledgement. Record
which faults are simulated exceptions and which terminate a process.

Posting writer or ledger integrity errors should roll back the chunk and remain
visible. A classified business rejection may be persisted separately with a reason,
audited disposition and reconciliation treatment. Review broad skip, `noRollback`,
independent `REQUIRES_NEW`, caught exceptions and checked exception rollback rules.
Listeners must tolerate retries and avoid untracked writes. Work performed from an
after-commit listener needs its own recovery path and cannot undo the committed chunk.

## Readers and scaling

| Strategy | Tradeoff and evidence |
| --- | --- |
| Cursor | Lower query churn with a long-lived cursor. Check transaction and connection lifetime, fetch size, restart-position cost and JDBC holdability. |
| JDBC paging | Use a unique, immutable, non-null sort key with a supporting index. Verify stable filter/scope and same data snapshot or replay rules after restart. |
| Keyset | A high-water mark bounds work over stable keys. Late arrivals, changed eligibility and reused keys still need reconciliation or a durable claim. |
| Partitioning | Give each worker a disjoint bounded partition and a separate checkpoint. Test shard boundaries and the failed partition's restart. |
| Claim table | Persist ownership and a monotonically advancing fence. Test concurrent and abandoned claims separately from reader correctness. |

Choose commit interval, fetch size and batch DML using the same fixture sizes and
failure scenarios across candidates. Measure throughput, p95 latency, peak heap,
pool saturation, lock waits, undo/WAL/redo, checkpoint overhead and restart cost.
Limit active workers by available connections and database contention. Confirm
correctness with independently computed balances and durable checkpoint evidence.

Sources [Spring Batch 5.2 domain and lifecycle](https://docs.spring.io/spring-batch/reference/5.2/domain.html),
[chunk processing](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing.html),
[readers](https://docs.spring.io/spring-batch/reference/5.2/readers-and-writers/database.html),
and [Spring transaction annotations](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/annotations.html).
