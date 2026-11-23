# Spring Batch engineering reference

Start with [the operational reference](../../.agents/skills/transaction-safe-engineering/references/spring-batch-safety.md).
Trace actual boot configuration, the step builder, and repository and business data
sources before recommending a restart. Record which fields identify the JobInstance
and preserve the step/checkpoint contract across attempts.

| Decision | Verification |
| --- | --- |
| Job identity | Relaunch a failed JobInstance using the same business date and type. Change a non-identifying operator parameter. Check same instance, distinct execution IDs, and rejection of a completed instance. |
| Step transaction | Record the manager used by the writer and metadata. Induce a failure after writing an item within the second chunk. Verify the second chunk and its checkpoint remained uncommitted. |
| Reader | Page by stable unique `event_key` over a frozen membership filter. Verify the resumed read count and exact expected item effects. |
| Retry and skip | Treat writer integrity errors as failures. Exercise explicit classified business rejection separately. For runtime retries, inspect exception policy and real rollback boundaries. |
| Concurrency and scale | Prove database uniqueness and claim fencing independently of `JobRepository` metadata. Use increasing volumes and record engine metrics. |

Observed fixture uses plain Spring Batch 5.2.6 with Spring JDBC, PostgreSQL and
Java 17-compatible compilation. The reader is initialized explicitly in the fixture
because a Spring container does not own that instance. Application code can use the
configured bean lifecycle. There is no claim that Spring Boot auto-configuration,
partition deployment, cursor holdability, or a different major Batch version ran.

Primary source bindings [Batch 5.2 lifecycle](https://docs.spring.io/spring-batch/reference/5.2/domain.html),
[paging reader at v5.2.6](https://github.com/spring-projects/spring-batch/blob/39c91c1c47eb752a5e64eb612c5e411c5e7f86d8/spring-batch-infrastructure/src/main/java/org/springframework/batch/item/database/JdbcPagingItemReader.java),
and [chunk transactions](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing.html).
