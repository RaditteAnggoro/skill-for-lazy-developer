-- Read-only closed-batch checks for the reference schema. Zero rows is the expected result.
-- Amounts are positive integral minor units. Each journal is single currency and has
-- exactly two lines. A reversal is one full inverse of the original, with its own key.
-- The fixture audit records one independent approval per journal. Run at a stable cut.
WITH lines_by_currency AS (
    SELECT event_key, currency, COUNT(*) AS line_count,
           SUM(CASE WHEN direction = 'D' THEN amount_minor ELSE 0 END) AS debit,
           SUM(CASE WHEN direction = 'C' THEN amount_minor ELSE 0 END) AS credit
    FROM ledger_entry GROUP BY event_key, currency
), stage_totals AS (
    SELECT batch_id, currency, COUNT(*) AS effects, SUM(amount_minor) AS amount
    FROM financial_stage WHERE state <> 'REJECTED' GROUP BY batch_id, currency
), journal_totals AS (
    SELECT batch_id, currency, COUNT(*) AS effects, SUM(amount_minor) AS amount
    FROM posting_journal GROUP BY batch_id, currency
), batch_keys AS (
    SELECT batch_id, currency FROM stage_totals
    UNION SELECT batch_id, currency FROM journal_totals
)
SELECT 'unbalanced_currency' AS invariant, l.event_key AS reference_id
FROM lines_by_currency l WHERE l.debit <> l.credit
UNION ALL
SELECT 'journal_incomplete', j.event_key FROM posting_journal j
LEFT JOIN lines_by_currency l ON l.event_key = j.event_key AND l.currency = j.currency
WHERE l.line_count IS NULL OR l.line_count <> 2 OR l.debit <> j.amount_minor OR l.credit <> j.amount_minor
   OR EXISTS (SELECT 1 FROM lines_by_currency x WHERE x.event_key = j.event_key AND x.currency <> j.currency)
UNION ALL
SELECT 'duplicate_effect', event_key FROM posting_journal GROUP BY event_key HAVING COUNT(*) <> 1
UNION ALL
SELECT 'invalid_ledger_line', event_key FROM ledger_entry
WHERE amount_minor <= 0 OR direction NOT IN ('D', 'C') OR line_no NOT IN (1, 2)
UNION ALL
SELECT 'accepted_unposted', s.event_key FROM financial_stage s
WHERE s.state NOT IN ('POSTED', 'REJECTED')
UNION ALL
SELECT 'posted_without_journal', s.event_key FROM financial_stage s LEFT JOIN posting_journal j ON j.event_key = s.event_key
WHERE s.state = 'POSTED' AND j.event_key IS NULL
UNION ALL
SELECT 'unexpected_posting', j.event_key FROM posting_journal j LEFT JOIN financial_stage s ON s.event_key = j.event_key
WHERE s.event_key IS NULL OR s.state <> 'POSTED'
UNION ALL
SELECT 'stage_journal_mismatch', j.event_key FROM posting_journal j JOIN financial_stage s ON s.event_key = j.event_key
WHERE j.fingerprint <> s.fingerprint OR j.amount_minor <> s.amount_minor OR j.currency <> s.currency
   OR j.batch_id <> s.batch_id OR j.kind <> s.kind OR j.reverses_key <> s.reverses_key
   OR (j.reverses_key IS NULL AND s.reverses_key IS NOT NULL) OR (j.reverses_key IS NOT NULL AND s.reverses_key IS NULL)
   OR j.adjusts_key <> s.adjusts_key
   OR (j.adjusts_key IS NULL AND s.adjusts_key IS NOT NULL) OR (j.adjusts_key IS NOT NULL AND s.adjusts_key IS NULL)
UNION ALL
SELECT 'effective_date_mismatch', j.event_key FROM posting_journal j JOIN financial_stage s ON s.event_key = j.event_key
WHERE j.business_date <> s.business_date OR j.value_date <> s.value_date
UNION ALL
SELECT 'reversal_mismatch', j.event_key FROM posting_journal j
LEFT JOIN posting_journal original ON original.event_key = j.reverses_key
WHERE (j.kind = 'REVERSAL' AND (original.event_key IS NULL OR original.kind <> 'POSTING'
    OR j.currency <> original.currency OR j.amount_minor <> original.amount_minor
    OR EXISTS (SELECT 1 FROM ledger_entry reversed WHERE reversed.event_key = j.event_key
      AND NOT EXISTS (SELECT 1 FROM ledger_entry source WHERE source.event_key = original.event_key
        AND reversed.account_code = source.account_code AND reversed.direction <> source.direction
        AND reversed.amount_minor = source.amount_minor AND reversed.currency = source.currency))))
   OR (j.kind <> 'REVERSAL' AND j.reverses_key IS NOT NULL)
UNION ALL
SELECT 'adjustment_mismatch', j.event_key FROM posting_journal j
LEFT JOIN posting_journal original ON original.event_key = j.adjusts_key
WHERE (j.kind = 'ADJUSTMENT' AND (original.event_key IS NULL OR original.kind <> 'POSTING'
    OR j.currency <> original.currency)) OR (j.kind <> 'ADJUSTMENT' AND j.adjusts_key IS NOT NULL)
UNION ALL
SELECT 'batch_total_mismatch', b.batch_id FROM batch_keys b
LEFT JOIN stage_totals s ON s.batch_id = b.batch_id AND s.currency = b.currency
LEFT JOIN journal_totals j ON j.batch_id = b.batch_id AND j.currency = b.currency
WHERE COALESCE(s.effects, 0) <> COALESCE(j.effects, 0) OR COALESCE(s.amount, 0) <> COALESCE(j.amount, 0)
UNION ALL
SELECT 'audit_missing_or_invalid', j.event_key FROM posting_journal j LEFT JOIN posting_audit a ON a.event_key = j.event_key
WHERE a.event_key IS NULL OR a.initiator = a.approver OR a.business_date <> j.business_date
   OR NULLIF(TRIM(a.correlation_id), '') IS NULL OR NULLIF(TRIM(a.reason_code), '') IS NULL
UNION ALL
SELECT 'outbox_missing', j.event_key FROM posting_journal j LEFT JOIN posting_outbox o ON o.event_key = j.event_key
WHERE o.event_key IS NULL;
