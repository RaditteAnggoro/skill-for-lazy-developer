package fixture;

import io.zonky.test.db.postgres.embedded.EmbeddedPostgres;
import org.junit.jupiter.api.*;
import org.springframework.batch.core.*;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.launch.support.TaskExecutorJobLauncher;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.repository.JobInstanceAlreadyCompleteException;
import org.springframework.batch.core.repository.support.JobRepositoryFactoryBean;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.item.database.Order;
import org.springframework.batch.item.database.builder.JdbcPagingItemReaderBuilder;
import org.springframework.batch.test.JobRepositoryTestUtils;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;

import javax.sql.DataSource;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.*;

import static org.junit.jupiter.api.Assertions.*;

class EnterpriseBatchTest {
    private static final String PAYLOAD = "a".repeat(64);
    private static final String OTHER_PAYLOAD = "b".repeat(64);
    private static EmbeddedPostgres server;
    private DataSource dataSource;
    private JdbcTemplate jdbc;

    @BeforeAll
    static void startDatabase() throws Exception {
        server = EmbeddedPostgres.builder().setServerConfig("listen_addresses", "127.0.0.1").start();
    }

    @AfterAll
    static void stopDatabase() throws Exception {
        if (server != null) server.close();
    }

    @BeforeEach
    void resetSyntheticSchema() throws Exception {
        dataSource = server.getPostgresDatabase();
        jdbc = new JdbcTemplate(dataSource);
        jdbc.setQueryTimeout(4);
        jdbc.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public");
        jdbc.execute(resource("postgresql-claim-and-post.sql"));
    }

    private static String resource(String name) throws Exception {
        try (var stream = new ClassPathResource(name).getInputStream()) {
            return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private void stage(String key) {
        fixtureEvent(key, "POSTING", null, "2026-11-20");
    }

    private void fixtureEvent(String key, String kind, String original, String valueDate) {
        jdbc.update("""
            INSERT INTO financial_stage(event_key, fingerprint, amount_minor, currency,
                business_date, value_date, batch_id, kind, reverses_key, adjusts_key)
            VALUES (?, ?, 125, 'IDR', DATE '2026-11-22', CAST(? AS date), 'batch-1', ?, ?, ?)
            """, key, PAYLOAD, valueDate, kind, kind.equals("REVERSAL") ? original : null,
            kind.equals("ADJUSTMENT") ? original : null);
    }

    private List<String> claim(String owner, int count) {
        return jdbc.queryForList("SELECT event_key FROM claim_financial_batch(?, ?, 120) ORDER BY event_key",
            String.class, owner, count);
    }

    private String post(String key, String owner, long version, String fingerprint) {
        return jdbc.queryForObject("SELECT post_financial_claim(?, ?, ?, ?)", String.class,
            key, owner, version, fingerprint);
    }

    private int count(String relation) {
        return jdbc.queryForObject("SELECT count(*) FROM " + relation, Integer.class);
    }

    private Set<String> observations() throws Exception {
        return Set.copyOf(jdbc.query(resource("ledger-invariants.sql"), (rs, row) -> rs.getString("invariant")));
    }

    @Test
    void disjointClaimsAndExpiredOwnershipAreEnforced() throws Exception {
        stage("a"); stage("b");
        try (var first = dataSource.getConnection(); var statement = first.createStatement()) {
            first.setAutoCommit(false);
            statement.setQueryTimeout(4);
            try (var rows = statement.executeQuery("SELECT event_key FROM claim_financial_batch('worker-A', 1, 60)")) {
                assertTrue(rows.next());
                assertEquals("a", rows.getString(1));
            }
            assertEquals(List.of("b"), claim("worker-B", 1));
            first.commit();
        }
        jdbc.update("UPDATE financial_stage SET lease_until = CURRENT_TIMESTAMP - interval '1 second' WHERE event_key = 'a'");
        assertEquals(1, jdbc.queryForObject("SELECT recover_financial_claims(1)", Integer.class));
        assertEquals(List.of("a"), claim("worker-C", 1));
        assertThrows(RuntimeException.class, () -> post("a", "worker-A", 1, PAYLOAD));
        assertEquals("POSTED", post("a", "worker-C", 3, PAYLOAD));
        assertEquals("POSTED", post("b", "worker-B", 1, PAYLOAD));
        assertEquals(Set.of(), observations());
    }

    @Test
    void concurrentReplayHasOneDurableEffectAndRejectsPayloadConflict() throws Exception {
        stage("same");
        claim("writer", 1);
        var ready = new CyclicBarrier(2);
        var workers = Executors.newFixedThreadPool(2);
        try {
            Callable<String> submit = () -> { ready.await(4, TimeUnit.SECONDS); return post("same", "writer", 1, PAYLOAD); };
            var first = workers.submit(submit);
            var second = workers.submit(submit);
            assertEquals(Set.of("POSTED", "ALREADY_POSTED"), Set.of(first.get(6, TimeUnit.SECONDS), second.get(6, TimeUnit.SECONDS)));
        } finally {
            workers.shutdownNow();
        }
        assertThrows(RuntimeException.class, () -> post("same", "writer", 1, OTHER_PAYLOAD));
        assertEquals(1, count("posting_journal"));
        assertEquals(2, count("ledger_entry"));
        assertEquals(1, count("posting_outbox"));
        assertEquals(Set.of(), observations());
    }

    @Test
    void inconsistentExpiredClaimWithExistingJournalRequiresReconciliation() throws Exception {
        stage("inconsistent"); claim("worker", 1); post("inconsistent", "worker", 1, PAYLOAD);
        jdbc.update("""
            UPDATE financial_stage SET state = 'CLAIMED', owner_id = 'lost-worker',
              lease_until = CURRENT_TIMESTAMP - interval '1 second' WHERE event_key = 'inconsistent'
            """);
        assertEquals(1, jdbc.queryForObject("SELECT recover_financial_claims(1)", Integer.class));
        assertEquals("RECONCILIATION_REQUIRED", jdbc.queryForObject("SELECT state FROM financial_stage", String.class));
        assertEquals(List.of(), claim("another-worker", 1));
        assertEquals(1, count("posting_journal"));
        assertTrue(observations().contains("unexpected_posting"));
    }

    @Test
    void chunkFailureRollsBackWriterAndRestartsFromDurablePagingCheckpoint() throws Exception {
        for (String key : List.of("a", "b", "c", "d")) stage(key);
        assertEquals(4, claim("batch", 4).size());
        new ResourceDatabasePopulator(new ClassPathResource("org/springframework/batch/core/schema-postgresql.sql")).execute(dataSource);
        var tx = new DataSourceTransactionManager(dataSource);
        var factory = new JobRepositoryFactoryBean();
        factory.setDataSource(dataSource);
        factory.setTransactionManager(tx);
        factory.afterPropertiesSet();
        var repository = factory.getObject();
        var launcher = new TaskExecutorJobLauncher();
        launcher.setJobRepository(repository);
        launcher.afterPropertiesSet();
        var parameters = new JobParametersBuilder().addString("businessDate", "2026-11-22", true)
            .addString("batchType", "repayment", true).addString("operator", "first", false).toJobParameters();
        try {
            var failed = launcher.run(job(repository, tx, true), parameters);
            assertEquals(BatchStatus.FAILED, failed.getStatus());
            assertEquals(2, count("posting_journal"), () -> failed.getAllFailureExceptions().toString());
            assertEquals(4, count("ledger_entry"));
            assertEquals(Set.of("accepted_unposted", "batch_total_mismatch"), observations());

            var retry = new JobParametersBuilder(parameters).addString("operator", "second", false).toJobParameters();
            var completed = launcher.run(job(repository, tx, false), retry);
            assertEquals(BatchStatus.COMPLETED, completed.getStatus());
            assertEquals(failed.getJobInstance().getId(), completed.getJobInstance().getId());
            assertNotEquals(failed.getId(), completed.getId());
            assertEquals(2, completed.getStepExecutions().iterator().next().getReadCount());
            assertEquals(4, count("posting_journal"));
            assertEquals(Set.of(), observations());
            assertThrows(JobInstanceAlreadyCompleteException.class, () -> launcher.run(job(repository, tx, false), retry));
        } finally {
            new JobRepositoryTestUtils(repository).removeJobExecutions();
        }
    }

    private Job job(JobRepository repository, DataSourceTransactionManager tx, boolean failWriter) throws Exception {
        var reader = new JdbcPagingItemReaderBuilder<String>().name("immutable-repayment-keys")
            .dataSource(dataSource).selectClause("SELECT event_key").fromClause("FROM financial_stage")
            .whereClause("WHERE batch_id = 'batch-1'").sortKeys(Map.of("event_key", Order.ASCENDING))
            .rowMapper((rs, row) -> rs.getString("event_key")).pageSize(2).fetchSize(2).saveState(true).build();
        // This test assembles the reader outside the container's bean lifecycle.
        reader.afterPropertiesSet();
        var step = new StepBuilder("post-chunks", repository).<String, String>chunk(2, tx).reader(reader)
            .writer(chunk -> {
                for (String key : chunk) {
                    assertEquals("POSTED", post(key, "batch", 1, PAYLOAD));
                    if (failWriter && key.equals("c")) throw new IllegalStateException("synthetic writer failure");
                }
            }).build();
        return new JobBuilder("repayment", repository).start(step).build();
    }

    @Test
    void reversedOrderDeadlocksAndOrderedRetrySucceeds() throws Exception {
        stage("a"); stage("b");
        var locked = new CyclicBarrier(2);
        var workers = Executors.newFixedThreadPool(2);
        try {
            var left = workers.submit(() -> lockPair("a", "b", locked));
            var right = workers.submit(() -> lockPair("b", "a", locked));
            assertEquals(Set.of("ok", "40P01"), Set.of(left.get(6, TimeUnit.SECONDS), right.get(6, TimeUnit.SECONDS)));
            assertEquals("ok", lockPair("a", "b", new CyclicBarrier(1)));
        } finally {
            workers.shutdownNow();
        }
    }

    private String lockPair(String first, String second, CyclicBarrier barrier) throws Exception {
        try (var connection = dataSource.getConnection(); var commands = connection.createStatement()) {
            connection.setAutoCommit(false);
            commands.execute("SET LOCAL deadlock_timeout = '100ms'; SET LOCAL lock_timeout = '3s'");
            try {
                lock(connection, first);
                barrier.await(4, TimeUnit.SECONDS);
                lock(connection, second);
                connection.commit();
                return "ok";
            } catch (SQLException error) {
                connection.rollback();
                return error.getSQLState();
            }
        }
    }

    private static void lock(Connection connection, String key) throws SQLException {
        try (var statement = connection.prepareStatement("SELECT event_key FROM financial_stage WHERE event_key = ? FOR UPDATE")) {
            statement.setString(1, key);
            try (var rows = statement.executeQuery()) { assertTrue(rows.next()); }
        }
    }

    @Test
    void processTerminationBeforeAndAfterCommitKeepsPostingAndOutboxConsistent() throws Exception {
        stage("crash"); claim("worker", 1);
        String token = UUID.randomUUID().toString();
        jdbc.execute("CREATE TABLE synthetic_fixture_guard (token varchar(80) PRIMARY KEY)");
        jdbc.update("INSERT INTO synthetic_fixture_guard VALUES (?)", token);
        assertEquals(81, childProcess(token, "before"));
        assertEquals(0, count("posting_journal"));
        assertEquals(0, count("ledger_entry"));
        assertEquals(82, childProcess(token, "after"));
        assertEquals("ALREADY_POSTED", post("crash", "worker", 1, PAYLOAD));
        assertEquals(2, count("ledger_entry"));
        assertEquals(1, count("posting_outbox"));
        jdbc.update("UPDATE posting_outbox SET delivery_state = 'UNKNOWN' WHERE event_key = 'crash'");
        assertEquals("ALREADY_POSTED", post("crash", "worker", 1, PAYLOAD));
        assertEquals("UNKNOWN", jdbc.queryForObject("SELECT delivery_state FROM posting_outbox", String.class));
        assertEquals(Set.of(), observations());
    }

    private int childProcess(String token, String boundary) throws Exception {
        var command = new ProcessBuilder(Path.of(System.getProperty("java.home"), "bin", "java").toString(),
            "-cp", System.getProperty("java.class.path"), PostingCrashWorker.class.getName(),
            Integer.toString(server.getPort()), token, boundary).inheritIO();
        Process child = command.start();
        try {
            assertTrue(child.waitFor(10, TimeUnit.SECONDS), "fixture worker did not terminate");
            return child.exitValue();
        } finally {
            if (child.isAlive()) child.destroyForcibly();
        }
    }

    @Test
    void backdatedReversalAndCorruptedRowsAreDistinguished() throws Exception {
        stage("initial"); claim("worker", 1); post("initial", "worker", 1, PAYLOAD);
        fixtureEvent("reversal", "REVERSAL", "initial", "2026-11-18");
        claim("worker", 1); post("reversal", "worker", 1, PAYLOAD);
        assertEquals(Set.of(), observations());
        jdbc.update("UPDATE ledger_entry SET amount_minor = 124 WHERE event_key = 'reversal' AND line_no = 1");
        jdbc.update("UPDATE posting_journal SET value_date = DATE '2026-11-22' WHERE event_key = 'reversal'");
        jdbc.update("DELETE FROM posting_audit WHERE event_key = 'reversal'");
        assertEquals(Set.of("unbalanced_currency", "journal_incomplete", "reversal_mismatch",
            "audit_missing_or_invalid", "effective_date_mismatch"), observations());
    }

    @Test
    void separateAdjustmentAndCrossCurrencyNegativeControl() throws Exception {
        stage("original"); claim("worker", 1); post("original", "worker", 1, PAYLOAD);
        fixtureEvent("adjust", "ADJUSTMENT", "original", "2026-11-22");
        claim("worker", 1); post("adjust", "worker", 1, PAYLOAD);
        assertEquals(Set.of(), observations());
        jdbc.update("UPDATE ledger_entry SET currency = 'USD' WHERE event_key = 'adjust' AND direction = 'C'");
        long overall = jdbc.queryForObject("""
            SELECT sum(CASE WHEN direction = 'D' THEN amount_minor ELSE -amount_minor END)
            FROM ledger_entry WHERE event_key = 'adjust'
            """, Long.class);
        assertEquals(0L, overall);
        assertEquals(Set.of("unbalanced_currency", "journal_incomplete"), observations());
        jdbc.update("UPDATE ledger_entry SET currency = 'IDR' WHERE event_key = 'adjust'");
        jdbc.update("UPDATE posting_journal SET adjusts_key = NULL WHERE event_key = 'adjust'");
        assertEquals(Set.of("stage_journal_mismatch", "adjustment_mismatch"), observations());
    }

    @Test
    void readsMeasuredPlanAndReconcilesGrowingWorkloadsInBoundedChunks() throws Exception {
        for (int size : List.of(500, 5000)) {
            jdbc.execute("TRUNCATE financial_stage CASCADE");
            jdbc.update("""
                INSERT INTO financial_stage(event_key, fingerprint, amount_minor, currency,
                    business_date, value_date, batch_id, kind)
                SELECT 'volume-' || lpad(i::text,6,'0'), repeat('a',64), i, 'IDR',
                    DATE '2026-11-22', DATE '2026-11-22', 'volume', 'POSTING'
                FROM generate_series(1, ?) i
                """, size);
            jdbc.execute("ANALYZE financial_stage");
            String plan = jdbc.queryForObject("""
                EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
                SELECT event_key FROM financial_stage WHERE state IN ('READY', 'RETRYABLE')
                ORDER BY event_key LIMIT 128
                """, String.class);
            assertNotNull(plan);
            assertTrue(plan.contains("Actual Rows") && plan.contains("Shared Hit Blocks"));
            var claimTimes = new ArrayList<Long>();
            long start = System.nanoTime(), peakHeap = 0;
            String initialWal = jdbc.queryForObject("SELECT pg_current_wal_insert_lsn()::text", String.class);
            while (true) {
                long claimStart = System.nanoTime();
                var keys = claim("volume", 128);
                if (keys.isEmpty()) break;
                claimTimes.add(System.nanoTime() - claimStart);
                assertTrue(keys.size() <= 128);
                for (String key : keys) assertEquals("POSTED", post(key, "volume", 1, PAYLOAD));
                var runtime = Runtime.getRuntime();
                peakHeap = Math.max(peakHeap, runtime.totalMemory() - runtime.freeMemory());
            }
            double elapsed = (System.nanoTime() - start) / 1e9;
            Collections.sort(claimTimes);
            double p95Millis = claimTimes.get((int) Math.ceil(0.95 * claimTimes.size()) - 1) / 1e6;
            long walBytes = jdbc.queryForObject(
                "SELECT pg_wal_lsn_diff(pg_current_wal_insert_lsn(), CAST(? AS pg_lsn))::bigint", Long.class, initialWal);
            assertEquals(size, count("posting_journal"));
            assertEquals(2 * size, count("ledger_entry"));
            assertEquals(Set.of(), observations());
            System.out.printf(java.util.Locale.ROOT,
                "VOLUME events=%d chunk=128 seconds=%.3f events_per_second=%.1f p95_claim_ms=%.3f sampled_used_heap_bytes=%d wal_bytes=%d%n",
                size, elapsed, size / elapsed, p95Millis, peakHeap, walBytes);
        }
    }
}
