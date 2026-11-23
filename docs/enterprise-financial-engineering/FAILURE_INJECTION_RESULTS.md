# Failure-injection evidence

The [enterprise fixture](../../tests/enhancement/fixtures/enterprise-batch/pom.xml)
starts its own loopback PostgreSQL database and accepts neither a remote JDBC URL
nor production credentials. The `PostingCrashWorker` only runs after checking a
synthetic nonce in the disposable database. The fixture uses real JDBC operations
and Spring Batch's persistent metadata tables.

| Requested scenario | Evidence |
| --- | --- |
| Failure before chunk commit and rollback during writer | Java writer exception after the first write of the second chunk. The first committed chunk remains, the failed chunk leaves zero effects, and the reader restarts with the two remaining items. |
| After successful commit and before local commit | Separate JVM halts with fixture exit 82 after commit and 81 before commit. Replay returns the prior result only for the committed case. |
| After/before checkpoint persistence | The Batch writer failure and restart verify persisted chunk boundaries. Killing the Spring Batch JVM between its metadata operations is a separate fault matrix. |
| Two queue workers and orphan claim | One connection holds a claim while another acquires a disjoint row. Expiry and recovery advance fences. A journal discovered on an inconsistent claim sends the item to reconciliation. |
| Lock contention and deadlock | Two workers deliberately acquire opposite row locks. PostgreSQL detects `40P01`; an ordered retry completes. |
| Duplicate, conflicting and completed replay | Concurrent same-key writers produce one journal, two lines and one outbox row. A different fingerprint fails. A completed Spring Batch instance refuses relaunch. |
| Unknown external outcome | Synthetic outbox `UNKNOWN` remains unresolved after local replay. No real provider request or acknowledgement was exercised. |
| Backdate, reversal, adjustment, imbalance and audit evidence | A backdated linked reversal and a separately keyed adjustment reconcile. Corrupt amounts, cross-currency sides, incorrect correction references, an altered value date, and missing audit evidence produce oracle findings. |
| Growing volume | Select and post in fixed chunks of at most 128, reconcile every row, and capture actual plan fields, observed latency, sampled heap and WAL. |

Measured wall time includes datasource connection and query overhead. Sampled JVM
heap is not OS RSS, and WAL is a database write-volume observation, not a production
load test. Independent PostgreSQL correctness tests cover the named cut points.
Power-loss durability, distributed throughput and Oracle integration remain separate.

Reproduce with `mvn -B -ntp -f tests/enhancement/fixtures/enterprise-batch/pom.xml test`.
See [dialect coverage](POSTGRESQL_ORACLE_COMPARISON.md) for the Oracle status.

## Local runs on 2026-11-23

All **9/9** integration tests passed on Temurin 17.0.21.1 and **9/9** on
Temurin 21.0.13 against the pinned PostgreSQL 18.3 engine and Batch 5.2.6.
Each workload reconciled every accepted effect and accounting line.

| JDK | Events | Seconds | Events/s | p95 claim ms | Sampled JVM heap bytes | WAL bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 17 | 500 | 3.630 | 137.8 | 8.124 | 90,589,696 | 1,084,416 |
| 17 | 5,000 | 36.953 | 135.3 | 15.967 | 83,107,872 | 10,627,904 |
| 21 | 500 | 3.765 | 132.8 | 8.442 | 88,424,576 | 1,084,416 |
| 21 | 5,000 | 34.051 | 146.8 | 9.952 | 76,425,464 | 10,627,904 |

The test checked actual rows and buffer fields from the local `EXPLAIN` plan.
These single-run measurements do not rank JDKs or establish an index speedup.
