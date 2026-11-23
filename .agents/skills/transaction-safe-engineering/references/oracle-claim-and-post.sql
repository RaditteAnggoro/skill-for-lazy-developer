-- Oracle 19c reference snippets, not a deployable migration. Use bound parameters.
-- Use the columns in the PostgreSQL reference with Oracle VARCHAR2 and NUMBER(19,0),
-- independent Oracle DDL, PKs/unique constraints, and TIMESTAMP WITH TIME ZONE leases.
-- Index (state, event_key), (state, lease_until, event_key), and (batch_id, currency, state).

-- Claim candidate IDs through a nonlocking, ordered, bounded scan. Bind a finite scan
-- limit. Concurrent changes may make the result stale before each locking probe.
SELECT event_key FROM (
    SELECT event_key FROM financial_stage WHERE state IN ('READY', 'RETRYABLE') ORDER BY event_key
) WHERE ROWNUM <= :scan_limit;

-- For each candidate use a zero-or-one-row explicit cursor or a singleton SELECT
-- INTO with NO_DATA_FOUND handling. Close the cursor before the next iteration.
-- The lock continues until commit. Skip empty results; never treat them as queue empty.
SELECT claim_version FROM financial_stage
WHERE event_key = :event_key AND state IN ('READY', 'RETRYABLE') FOR UPDATE SKIP LOCKED;

UPDATE financial_stage SET state = 'CLAIMED', owner_id = :owner_id,
    claim_version = claim_version + 1,
    lease_until = SYSTIMESTAMP + NUMTODSINTERVAL(:lease_seconds, 'SECOND')
WHERE event_key = :event_key AND claim_version = :locked_version AND state IN ('READY', 'RETRYABLE');

-- Require SQL%ROWCOUNT = 1, capture the new token, stop at the claim limit,
-- and commit once. Reject invalid/nonpositive bounds before locking. No DDL in this TX.

-- Recovery candidates use an ordered bounded scan by (lease_until, event_key). For
-- each, lock the singleton with SKIP LOCKED and recheck state and expiry in the UPDATE.
SELECT event_key FROM (
    SELECT event_key FROM financial_stage WHERE state = 'CLAIMED' AND lease_until <= SYSTIMESTAMP
    ORDER BY lease_until, event_key
) WHERE ROWNUM <= :scan_limit;

SELECT claim_version FROM financial_stage
WHERE event_key = :event_key AND state = 'CLAIMED' AND lease_until <= SYSTIMESTAMP FOR UPDATE SKIP LOCKED;

UPDATE financial_stage SET state = CASE
        WHEN EXISTS (SELECT 1 FROM posting_journal WHERE event_key = :event_key) THEN 'RECONCILIATION_REQUIRED'
        ELSE 'RETRYABLE' END, owner_id = NULL, lease_until = NULL,
    claim_version = claim_version + 1
WHERE event_key = :event_key AND state = 'CLAIMED' AND claim_version = :locked_version
    AND lease_until <= SYSTIMESTAMP;

-- Posting owns a separate short TX. Use a bounded lock wait and reread on retry.
SELECT state, owner_id, claim_version, fingerprint, lease_until, amount_minor, currency,
       business_date, value_date, batch_id, kind, reverses_key, adjusts_key
FROM financial_stage WHERE event_key = :event_key FOR UPDATE WAIT 5;

-- Under the lock validate the fingerprint, owner, token and lease. If POSTED, read
-- the matching journal and return its result only for the same immutable payload.
-- Otherwise insert journal, both lines, audit and outbox, then fence this update.
-- A uniqueness error requires rollback and re-reading the winner in a fresh TX.
SELECT fingerprint, amount_minor, currency, kind FROM posting_journal WHERE event_key = :event_key;

INSERT INTO posting_journal (event_key, fingerprint, amount_minor, currency,
    business_date, value_date, batch_id, kind, reverses_key, adjusts_key)
VALUES (:event_key, :fingerprint, :amount_minor, :currency, :business_date,
    :value_date, :batch_id, :kind, :reverses_key, :adjusts_key);

-- Derive both line directions from the authorized journal or its original reversal
-- target. Validate equal amounts, opposite directions and the declared currency.
INSERT ALL
    INTO ledger_entry (event_key, line_no, account_code, direction, currency, amount_minor)
        VALUES (:event_key, 1, :account_one, :direction_one, :currency, :amount_minor)
    INTO ledger_entry (event_key, line_no, account_code, direction, currency, amount_minor)
        VALUES (:event_key, 2, :account_two, :direction_two, :currency, :amount_minor)
SELECT 1 FROM dual;

INSERT INTO posting_audit (event_key, initiator, approver, correlation_id, reason_code, recorded_at, business_date)
VALUES (:event_key, :initiator, :approver, :correlation_id, :reason_code, SYSTIMESTAMP, :business_date);
INSERT INTO posting_outbox (event_key, delivery_state) VALUES (:event_key, 'PENDING');

UPDATE financial_stage SET state = 'POSTED', owner_id = NULL, lease_until = NULL
WHERE event_key = :event_key AND state = 'CLAIMED' AND owner_id = :owner_id AND claim_version = :claim_version;
-- If SQL%ROWCOUNT is not one, roll back all posting writes. Verify with ledger-invariants.sql.
