import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.analyze_financial_source import RULES, analyze
from scripts.context_optimizer import RawEvidenceStore, optimize_case, select_financial_references
from scripts.run_financial_skill_benchmark import grade


JAVA_RISK = '''
import java.sql.SQLException;
import java.math.BigDecimal;
class Unsafe {
    @Transactional private void claim() {}
    void post() { this.claim(); }
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    void write() throws SQLException { try { repo.insert(); } catch (SQLException e) { log(e); } }
    void process() { repo.save(); repo.update(); repo.findAll(); }
    void configure() { step.skip(Exception.class); }
    void indexed() { if (!repo.existsById(key)) repo.insert(); }
    void precision() { new BigDecimal(-0.1); }
    void connect() { var connection = ds.getConnection(); }
}
'''
JAVA_SAFE = '''
import java.sql.SQLException;
import java.math.BigDecimal;
class Bounded {
    @Transactional(rollbackFor = SQLException.class)
    public void write() throws SQLException {
        try (var connection = ds.getConnection()) { otherBean.save(); }
        catch (SQLException exception) { throw exception; }
        repo.findChunk(page, 100);
        new BigDecimal("0.10");
    }
    void configure() { step.skip(ClassifiedBusinessRejection.class); }
    void indexed() { repo.atomicInsert(key); }
}
'''
SQL_RISK = '''
SELECT id FROM source ORDER BY id OFFSET 100 ROWS FETCH FIRST 5 ROWS ONLY;
INSERT INTO posting_journal(event_key) VALUES ('synthetic');
UPDATE financial_stage SET state='POSTED', owner_id=NULL WHERE event_key=:key;
SELECT id FROM stage FOR UPDATE; SELECT id FROM journals FOR UPDATE; COMMIT;
SELECT id FROM journals FOR UPDATE; SELECT id FROM stage FOR UPDATE; COMMIT;
ALTER TABLE source ADD score integer NOT NULL;
DROP TABLE old_fixture;
'''
SQL_SAFE = '''
-- DROP TABLE, OFFSET and TRUNCATE in a comment must not match.
CREATE TABLE posting_journal (event_key varchar(80), PRIMARY KEY (event_key));
INSERT INTO posting_journal(event_key) VALUES ('OFFSET');
SELECT id FROM source WHERE id > :last ORDER BY id FETCH FIRST 5 ROWS ONLY;
UPDATE financial_stage SET state='POSTED', owner_id=NULL
WHERE event_key=:key AND owner_id=:owner AND claim_version=:version;
SELECT id FROM stage FOR UPDATE; SELECT id FROM journals FOR UPDATE; COMMIT;
SELECT id FROM stage FOR UPDATE; SELECT id FROM journals FOR UPDATE; COMMIT;
CREATE INDEX CONCURRENTLY stage_id ON stage(id);
'''


class FinancialSourceTests(unittest.TestCase):
    def generate(self, root, name, data):
        file = Path(root) / name
        file.write_text(data, encoding='utf-8')
        return file

    @unittest.skipUnless(shutil.which('java'), 'Java source analysis requires JDK 17+')
    def test_java_ast_positive_and_negative_controls(self):
        with tempfile.TemporaryDirectory() as root:
            risk = self.generate(root, 'Unsafe.java', JAVA_RISK)
            safe = self.generate(root, 'Bounded.java', JAVA_SAFE)
            findings = analyze([risk, safe])
            self.assertEqual({row['rule'] for row in findings}, {rule for rule in RULES if rule.startswith('JAVA_')})
            self.assertTrue(all(row['file'] == risk.name and row['line'] > 0 and row['method'] for row in findings))
            confirmed = {row['rule'] for row in findings if row['classification'] == 'CONFIRMED'}
            self.assertEqual(confirmed, {'JAVA_DECIMAL_FLOAT'})

    def test_sql_positive_and_negative_controls_and_manual_disposition(self):
        with tempfile.TemporaryDirectory() as root:
            risk = self.generate(root, 'unsafe.sql', SQL_RISK)
            safe = self.generate(root, 'bounded.sql', SQL_SAFE)
            findings = analyze([risk, safe])
            self.assertEqual({row['rule'] for row in findings}, {rule for rule in RULES if rule.startswith('SQL_')})
            self.assertTrue(all(row['file'] == risk.name for row in findings))
            selected = next(row for row in findings if row['rule'] == 'SQL_MIGRATION_LOCK')
            reviewed = self.generate(root, 'checked.json', json.dumps([{**selected, 'evidence': 'Synthetic change reviewed'}]))
            updated = analyze([risk, safe], reviewed=reviewed)
            self.assertTrue(any(row['classification'] == 'FALSE_POSITIVE' for row in updated))

    def test_financial_reference_selection_preserves_ordinary_routes(self):
        self.assertEqual(select_financial_references('Improve a Spring Batch progress indicator'), [])
        self.assertEqual(select_financial_references('Fix a settings label', 'ledger reconciliation'), [])
        self.assertEqual(select_financial_references('Rename the loan dashboard title', 'ledger reconciliation'), [])
        self.assertEqual(select_financial_references('Review Spring Batch loan posting restart'),
                         ['spring-batch-safety.md', 'staging-posting-pipeline.md'])
        selected = select_financial_references('Periksa rekonsiliasi saldo dan audit', 'database')
        self.assertEqual(selected, ['ledger-invariants.sql', 'sql-performance-and-change-safety.md'])

    def test_benchmark_oracle_penalizes_misses_and_false_alarms(self):
        rows = [{'anchor': 'BatchLoanWriter.java:6', 'repair': 'decimal input', 'test': 'exact amount'},
                {'anchor': 'ExactAmount.java:5', 'repair': 'replace', 'test': ''}]
        result = grade(rows)
        self.assertEqual((result['true_positives'], result['false_positives'], result['false_negatives']), (1, 1, 3))

    def test_financial_context_requires_current_verified_project_memory(self):
        base = {'scope': {'project': 'demo'}, 'trust': 'verified', 'status': 'active', 'project_fingerprint': 'local'}
        records = [{**base, 'id': 'eligible'}, {**base, 'id': 'foreign', 'project_fingerprint': 'other'},
                   {**base, 'id': 'stale', 'status': 'stale'}, {**base, 'id': 'guess', 'trust': 'unverified'},
                   {**base, 'id': 'expired', 'review_after': '2000-01-01T00:00:00Z'}]
        task = {'id': 'sample', 'task': 'Review loan posting and ledger balance', 'project': 'demo',
                'project_fingerprint': 'local', 'memory': records}
        with tempfile.TemporaryDirectory() as root:
            result = optimize_case(task, RawEvidenceStore(root))
        self.assertEqual(result['selected_memory'], ['eligible'])
        self.assertIn('ledger-invariants.sql', result['financial_references'])
