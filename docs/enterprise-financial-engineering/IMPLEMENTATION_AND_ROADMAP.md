# Implementation and roadmap

| Phase | Delivered evidence |
| --- | --- |
| 1–2. Audit and research | [Baseline audit](CURRENT_CAPABILITY_AUDIT.md) and pinned source inventory below. |
| 3–5. Financial references | [Spring Batch](SPRING_BATCH_ENGINEERING_REFERENCE.md), [staging](STAGING_POSTING_ARCHITECTURE.md), [dialects](POSTGRESQL_ORACLE_COMPARISON.md), and [ledger invariants](LEDGER_AND_IDEMPOTENCY_INVARIANTS.md). |
| 6–7. Safety checks and faults | [Source review](JAVA_SQL_STATIC_ANALYSIS.md), positive/negative controls, and [real database and framework tests](FAILURE_INJECTION_RESULTS.md). |
| 8–9. SQL changes and accountability | [Performance and migration reference](../../.agents/skills/transaction-safe-engineering/references/sql-performance-and-change-safety.md) and [traceability evidence](SECURITY_AND_REGULATORY_TRACEABILITY.md). The existing transaction and release skills cover this intent. |
| 10–11. Context and comparison | The router and context selector load focused enterprise references. Financial memory requires a verified, active and current record, with matching root evidence when the caller supplies it. The [matched benchmark](SKILL_AB_BENCHMARK.md) compares the original skill, expanded references, source analysis and selected context. |
| 12. Verification | 17 skills and 300 Python unit tests passed at the end of the financial audit. The PostgreSQL/Spring Batch fixture passed 9/9 on each JDK and has a scoped GitHub workflow. |

## Public reference inventory

Ownership, repository status and pinned source were inspected on 2026-11-23.
All listed repositories were unarchived at inspection. These citations identify
the source inspected, separate from the artifact versions pinned for the tests.

| Reference | Source observation and decision |
| --- | --- |
| [Spring Batch](https://github.com/spring-projects/spring-batch/blob/39c91c1c47eb752a5e64eb612c5e411c5e7f86d8/spring-batch-infrastructure/src/main/java/org/springframework/batch/item/database/JdbcPagingItemReader.java#L52) · Apache-2.0 | v5.2.6 reader resumes by last sort key. Tested with JDBC metadata and a unique key. |
| [Spring Boot](https://github.com/spring-projects/spring-boot/blob/c069bce9fb096f7e146695459d69bf653dece1e6/spring-boot-project/spring-boot-autoconfigure/src/main/java/org/springframework/boot/autoconfigure/batch/BatchAutoConfiguration.java#L79) · Apache-2.0 | Boot wiring handles batch auto-configuration. The fixture assembles its own Batch infrastructure to make the resource boundary visible. |
| [Spring Framework](https://github.com/spring-projects/spring-framework/blob/1f1a81d634ffc1b7f2437d6ea4d983863a57a242/spring-tx/src/main/java/org/springframework/transaction/interceptor/TransactionAspectSupport.java#L322) · Apache-2.0 | Transaction interception informs the proxy and checked-exception diagnostics. Use target-version behavior when reviewing a project. |
| [Testcontainers Java](https://github.com/testcontainers/testcontainers-java/blob/9f7ada889f53e97f8358806c18deb7c25dda66f7/modules/postgresql/src/main/java/org/testcontainers/postgresql/PostgreSQLContainer.java#L89) · MIT | Container-owned JDBC URL provides an isolation pattern. Docker was unavailable; the runnable suite uses embedded PostgreSQL. |
| [pgjdbc](https://github.com/pgjdbc/pgjdbc/blob/c97aac7f2aeab6c09378be9140720648148e7f29/pgjdbc/src/main/java/org/postgresql/core/v3/QueryExecutorImpl.java#L442) · BSD-2-Clause | Fetch-size configuration reaches the query executor. The fixture pins driver 42.7.14. Check cursor behavior against actual batch settings. |
| [jOOQ](https://github.com/jOOQ/jOOQ/blob/32ac045d3c278893ca7866042f5b30dc64ef0fb2/jOOQ/src/main/java/org/jooq/impl/SelectQueryImpl.java#L2092) · Apache-2.0 OSS source | Dialect-specific locking rendering reinforces independent database tests. Edition and supported target dialect need a separate adoption review. |
| [Semgrep](https://github.com/semgrep/semgrep/blob/c4dbe9ee2fc6d0022ba02ef6b97c5954ed9549e3/src/engine/Match_rules.ml#L48) · LGPL-2.1 license text in repository | Engine has bounded pattern matching and distinct result processing. Registry rules, proprietary products and their licenses require separate review. |
| [ast-grep](https://github.com/ast-grep/ast-grep/blob/8a92260ad4b65cf4b716518a76b919e6f0d051b8/crates/core/src/matcher.rs#L54) · MIT | Structural matching is useful for finding candidates; the fixture selects the existing JDK parser to avoid a new core dependency. |
| [JavaParser](https://github.com/javaparser/javaparser/blob/6bc206c4ac26b24d8a4d5b8acf69fa105b9c026e/javaparser-core/src/main/java/com/github/javaparser/JavaParser.java#L96) · Apache-2.0 or LGPL | Language levels and symbol solving are candidates for a future cross-class scanner. This release uses compiler trees on the available JDK. |
| [Zonky Embedded PostgreSQL](https://github.com/zonkyio/embedded-postgres/blob/89b6805a64d1d1fe6e3113923dd08f46246152b3/src/main/java/io/zonky/test/db/postgres/embedded/EmbeddedPostgres.java#L254) · Apache-2.0 | Launches a disposable PostgreSQL engine; used as a test-only dependency with platform binaries. |
| [Flyway](https://github.com/flyway/flyway/blob/106acda188f75d033976f0eb41025de376667122/flyway-core/src/main/java/org/flywaydb/core/Flyway.java#L365) · Apache-2.0 OSS source | Migration validation informs cutover checks. Proprietary edition capabilities and licensing are separate. |
| [TigerBeetle](https://github.com/tigerbeetle/tigerbeetle/blob/a2a3c7064519e08233abe26c54a43fca2f9ad9bc/src/state_machine.zig#L3971) · Apache-2.0 | Existing-transfer comparison illustrates per-field mismatch rejection. The fixture implements its own SQL and does not introduce a second ledger runtime. |

The implementation uses public dependency artifacts in the isolated fixture.
Examples and test logic are original. No third-party source was transferred into
the pack. Official [PostgreSQL](https://www.postgresql.org/docs/18/) and
[Oracle](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/)
documentation inform the dialect-specific design.

## Remaining validation

- Run the fence, duplicate-payload, deadlock and reconciliation cases on an explicitly
  authorized disposable Oracle installation. Validate lock plans and DDL behavior.
- Terminate the Spring Batch process during metadata persistence and rehearse controlled
  recovery of a stale execution. Expand non-retryable business rejection and external
  unknown-outcome cases with a disposable provider simulator.
- Add multi-currency and partial-reversal cases when the consuming schema supplies those
  rules. Evaluate plan and migration changes using matched engine workloads.
- Extend the hidden write-and-grade comparison beyond SQLite to framework-backed
  repairs and evaluate independent regression-test quality before broader claims.

## Financial audit change manifest

The standalone financial audit used baseline `66b12c3`. The files below list
its implementation scope. Build output, toolchain caches, and test logs are ignored.

```text
.agents/skills/adaptive-workflow/SKILL.md
.agents/skills/transaction-safe-engineering/SKILL.md
.agents/skills/transaction-safe-engineering/references/ledger-invariants.sql
.agents/skills/transaction-safe-engineering/references/oracle-claim-and-post.sql
.agents/skills/transaction-safe-engineering/references/postgresql-claim-and-post.sql
.agents/skills/transaction-safe-engineering/references/spring-batch-safety.md
.agents/skills/transaction-safe-engineering/references/sql-performance-and-change-safety.md
.agents/skills/transaction-safe-engineering/references/staging-posting-pipeline.md
.github/workflows/financial-fixtures.yml
.gitignore
CHANGELOG.md
docs/VALIDATION.md
docs/enterprise-financial-engineering/CURRENT_CAPABILITY_AUDIT.md
docs/enterprise-financial-engineering/FAILURE_INJECTION_RESULTS.md
docs/enterprise-financial-engineering/IMPLEMENTATION_AND_ROADMAP.md
docs/enterprise-financial-engineering/JAVA_SQL_STATIC_ANALYSIS.md
docs/enterprise-financial-engineering/LEDGER_AND_IDEMPOTENCY_INVARIANTS.md
docs/enterprise-financial-engineering/POSTGRESQL_ORACLE_COMPARISON.md
docs/enterprise-financial-engineering/SECURITY_AND_REGULATORY_TRACEABILITY.md
docs/enterprise-financial-engineering/SKILL_AB_BENCHMARK.md
docs/enterprise-financial-engineering/SPRING_BATCH_ENGINEERING_REFERENCE.md
docs/enterprise-financial-engineering/STAGING_POSTING_ARCHITECTURE.md
docs/upstream-benchmark/07_REMAINING_ROADMAP.md
scripts/FinancialJavaScan.java
scripts/analyze_financial_source.py
scripts/build_release.py
scripts/check_transaction_safety.py
scripts/context_optimizer.py
scripts/run_financial_skill_benchmark.py
tests/enhancement/fixtures/enterprise-batch/README.md
tests/enhancement/fixtures/enterprise-batch/pom.xml
tests/enhancement/fixtures/enterprise-batch/src/test/java/fixture/EnterpriseBatchTest.java
tests/enhancement/fixtures/enterprise-batch/src/test/java/fixture/PostingCrashWorker.java
tests/enhancement/fixtures/financial-review/BatchLoanWriter.java
tests/enhancement/fixtures/financial-review/ExactAmount.java
tests/enhancement/fixtures/financial-review/finalize.sql
tests/test_financial_source.py
```
