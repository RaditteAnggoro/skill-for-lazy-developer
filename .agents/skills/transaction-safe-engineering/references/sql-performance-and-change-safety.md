# SQL performance, schema changes and auditability

## Diagnose performance on a bounded fixture

Read query text, JDBC bind types, predicates, statistics, actual row volume,
partitioning and concurrent workload. For `EXPLAIN`, identify physical access
and estimated rows. For actual evidence, compare actual rows per loop, scan/join
strategy, partition pruning, buffer hits/reads, temporary work, lock waits and
write amplification. PostgreSQL `EXPLAIN ANALYZE` executes the statement. Run
it on disposable data or after separate authorization for the exact scope.
For Oracle use the cursor plan plus eligible execution statistics for the same
binds. Estimated `EXPLAIN PLAN` alone does not verify a runtime plan.

For a staging queue, measure claim latency alongside posting throughput, WAL or
redo, heap, pool pressure and the recovery time after interruption. Compare the
same workload, data distribution, concurrency, statistics and cache conditions.
Declare a measured benefit only when the compared results support it.

## Migrate and reconcile incrementally

Record target version, DDL lock class, worst-case blockers and compatible client
versions. Expand first, then dual-read or dual-write only with durable reconciliation,
backfill in bounded resumable chunks, validate, cut over, and contract after the
observation window. Establish expected counts, key sets, currency totals and
invariants for every checkpoint. Rehearse the abort threshold and forward repair
if a successful DDL cannot be rolled back. PostgreSQL concurrent index creation
has transaction-block and invalid-index recovery constraints. Oracle DDL can
commit implicitly. Assess each engine and operation independently.

## Record accountable evidence

Record initiator, approver, scoped authorization, UTC system time, business date,
value date, correlation/key, and reason. Where appropriate retain minimal
before/after values or their fingerprints. Store append-only audit events with
restricted write and read access, test tamper detection, and verify declared
retention and restore behavior. Use synthetic or masked identifiers and minimize
fixture output. A generic audit checklist does not establish legal compliance.
Map the applicable version, provision and control to evidence when a regulator,
product or payment interface is in scope.

Sources [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html),
[concurrent index operations](https://www.postgresql.org/docs/18/sql-createindex.html),
[Oracle DBMS_XPLAN](https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_XPLAN.html),
and [Oracle COMMIT](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/COMMIT.html).
