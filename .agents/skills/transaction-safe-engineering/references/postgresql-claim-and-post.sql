-- Disposable reference schema. Use a dedicated synthetic database only.
CREATE TABLE financial_stage (
    event_key varchar(80) PRIMARY KEY,
    fingerprint varchar(64) NOT NULL CHECK (length(fingerprint) = 64),
    amount_minor bigint NOT NULL CHECK (amount_minor > 0),
    currency char(3) NOT NULL,
    business_date date NOT NULL,
    value_date date NOT NULL,
    batch_id varchar(80) NOT NULL,
    kind varchar(12) NOT NULL CHECK (kind IN ('POSTING', 'REVERSAL', 'ADJUSTMENT')),
    reverses_key varchar(80),
    adjusts_key varchar(80),
    state varchar(24) NOT NULL DEFAULT 'READY'
        CHECK (state IN ('READY', 'CLAIMED', 'POSTED', 'FAILED', 'RETRYABLE', 'REJECTED', 'RECONCILIATION_REQUIRED', 'COMPENSATING')),
    owner_id varchar(80),
    lease_until timestamp with time zone,
    claim_version bigint NOT NULL DEFAULT 0 CHECK (claim_version >= 0),
    CHECK ((state = 'CLAIMED' AND owner_id IS NOT NULL AND lease_until IS NOT NULL)
        OR (state <> 'CLAIMED' AND owner_id IS NULL AND lease_until IS NULL))
);
CREATE INDEX financial_stage_ready ON financial_stage (event_key) WHERE state IN ('READY', 'RETRYABLE');
CREATE INDEX financial_stage_expiry ON financial_stage (lease_until, event_key) WHERE state = 'CLAIMED';
CREATE INDEX financial_stage_batch ON financial_stage (batch_id, currency, state);

CREATE TABLE posting_journal (
    event_key varchar(80) PRIMARY KEY REFERENCES financial_stage(event_key),
    fingerprint varchar(64) NOT NULL,
    amount_minor bigint NOT NULL CHECK (amount_minor > 0),
    currency char(3) NOT NULL,
    business_date date NOT NULL,
    value_date date NOT NULL,
    batch_id varchar(80) NOT NULL,
    kind varchar(12) NOT NULL CHECK (kind IN ('POSTING', 'REVERSAL', 'ADJUSTMENT')),
    reverses_key varchar(80) UNIQUE REFERENCES posting_journal(event_key),
    adjusts_key varchar(80) REFERENCES posting_journal(event_key)
);
CREATE TABLE ledger_entry (
    event_key varchar(80) NOT NULL REFERENCES posting_journal(event_key),
    line_no integer NOT NULL,
    account_code varchar(24) NOT NULL,
    direction char(1) NOT NULL CHECK (direction IN ('D', 'C')),
    currency char(3) NOT NULL,
    amount_minor bigint NOT NULL CHECK (amount_minor > 0),
    PRIMARY KEY (event_key, line_no)
);
CREATE TABLE posting_audit (
    event_key varchar(80) PRIMARY KEY REFERENCES posting_journal(event_key),
    initiator varchar(80) NOT NULL,
    approver varchar(80) NOT NULL,
    correlation_id varchar(80) NOT NULL,
    reason_code varchar(32) NOT NULL,
    recorded_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    business_date date NOT NULL,
    CHECK (initiator <> approver)
);
CREATE TABLE posting_outbox (
    event_key varchar(80) PRIMARY KEY REFERENCES posting_journal(event_key),
    delivery_state varchar(12) NOT NULL DEFAULT 'PENDING' CHECK (delivery_state IN ('PENDING', 'UNKNOWN', 'ACKED'))
);

CREATE FUNCTION claim_financial_batch(p_owner varchar, p_limit integer, p_lease_seconds integer)
RETURNS SETOF financial_stage LANGUAGE plpgsql AS $$
BEGIN
    IF p_owner IS NULL OR p_owner = '' OR p_limit IS NULL OR p_limit NOT BETWEEN 1 AND 1000
        OR p_lease_seconds IS NULL OR p_lease_seconds NOT BETWEEN 1 AND 3600 THEN
        RAISE EXCEPTION 'invalid claim bounds' USING ERRCODE = '22023';
    END IF;
    RETURN QUERY WITH picked AS (
        SELECT s.event_key FROM financial_stage s
        WHERE s.state IN ('READY', 'RETRYABLE')
        ORDER BY s.event_key LIMIT p_limit FOR UPDATE SKIP LOCKED
    )
    UPDATE financial_stage s SET state = 'CLAIMED', owner_id = p_owner,
        lease_until = statement_timestamp() + make_interval(secs => p_lease_seconds),
        claim_version = s.claim_version + 1
    FROM picked WHERE s.event_key = picked.event_key RETURNING s.*;
END $$;

CREATE FUNCTION recover_financial_claims(p_limit integer) RETURNS integer LANGUAGE plpgsql AS $$
DECLARE recovered integer;
BEGIN
    IF p_limit IS NULL OR p_limit NOT BETWEEN 1 AND 1000 THEN
        RAISE EXCEPTION 'invalid recovery bounds' USING ERRCODE = '22023';
    END IF;
    WITH expired AS (
        SELECT s.event_key FROM financial_stage s
        WHERE s.state = 'CLAIMED' AND s.lease_until <= statement_timestamp()
        ORDER BY s.lease_until, s.event_key LIMIT p_limit FOR UPDATE SKIP LOCKED
    )
    UPDATE financial_stage s SET state = CASE
            WHEN EXISTS (SELECT 1 FROM posting_journal j WHERE j.event_key = s.event_key) THEN 'RECONCILIATION_REQUIRED'
            ELSE 'RETRYABLE' END, owner_id = NULL, lease_until = NULL,
        claim_version = s.claim_version + 1 FROM expired WHERE s.event_key = expired.event_key;
    GET DIAGNOSTICS recovered = ROW_COUNT;
    RETURN recovered;
END $$;

-- The caller owns commit/rollback. External delivery starts from the committed outbox.
CREATE FUNCTION post_financial_claim(p_key varchar, p_owner varchar, p_version bigint, p_fingerprint varchar)
RETURNS varchar LANGUAGE plpgsql AS $$
DECLARE s financial_stage%ROWTYPE; original posting_journal%ROWTYPE;
BEGIN
    SELECT * INTO STRICT s FROM financial_stage WHERE event_key = p_key FOR UPDATE;
    IF s.fingerprint IS DISTINCT FROM p_fingerprint THEN
        RAISE EXCEPTION 'same key has a different immutable payload' USING ERRCODE = '22023';
    END IF;
    IF s.state = 'POSTED' THEN
        IF NOT EXISTS (SELECT 1 FROM posting_journal j WHERE j.event_key = p_key AND j.fingerprint = p_fingerprint) THEN
            RAISE EXCEPTION 'posted stage has no matching journal' USING ERRCODE = '23514';
        END IF;
        RETURN 'ALREADY_POSTED';
    END IF;
    IF s.state <> 'CLAIMED' OR s.owner_id IS DISTINCT FROM p_owner
        OR s.claim_version IS DISTINCT FROM p_version OR s.lease_until <= clock_timestamp() THEN
        RAISE EXCEPTION 'claim is stale or belongs to another worker' USING ERRCODE = '55000';
    END IF;
    -- The fixture allows one full reversal and a separately keyed, approved adjustment.
    IF s.kind = 'REVERSAL' THEN
        SELECT * INTO STRICT original FROM posting_journal WHERE event_key = s.reverses_key;
        IF original.kind <> 'POSTING' OR s.currency <> original.currency OR s.amount_minor <> original.amount_minor
            OR s.adjusts_key IS NOT NULL THEN
            RAISE EXCEPTION 'reversal disagrees with original posting' USING ERRCODE = '22023';
        END IF;
    ELSIF s.kind = 'ADJUSTMENT' THEN
        SELECT * INTO STRICT original FROM posting_journal WHERE event_key = s.adjusts_key;
        IF original.kind <> 'POSTING' OR s.currency <> original.currency OR s.reverses_key IS NOT NULL THEN
            RAISE EXCEPTION 'adjustment disagrees with original posting' USING ERRCODE = '22023';
        END IF;
    ELSIF s.reverses_key IS NOT NULL OR s.adjusts_key IS NOT NULL THEN
        RAISE EXCEPTION 'unexpected correction reference' USING ERRCODE = '22023';
    END IF;
    INSERT INTO posting_journal (event_key, fingerprint, amount_minor, currency, business_date,
        value_date, batch_id, kind, reverses_key, adjusts_key)
    VALUES (s.event_key, s.fingerprint, s.amount_minor, s.currency, s.business_date,
        s.value_date, s.batch_id, s.kind, s.reverses_key, s.adjusts_key);
    INSERT INTO ledger_entry VALUES
        (s.event_key, 1, 'CASH', CASE WHEN s.kind = 'REVERSAL' THEN 'C' ELSE 'D' END, s.currency, s.amount_minor),
        (s.event_key, 2, 'RECEIVABLE', CASE WHEN s.kind = 'REVERSAL' THEN 'D' ELSE 'C' END, s.currency, s.amount_minor);
    INSERT INTO posting_audit (event_key, initiator, approver, correlation_id, reason_code, business_date)
        VALUES (s.event_key, 'fixture-initiator', 'fixture-approver', s.event_key, s.kind, s.business_date);
    INSERT INTO posting_outbox (event_key) VALUES (s.event_key);
    UPDATE financial_stage SET state = 'POSTED', owner_id = NULL, lease_until = NULL WHERE event_key = p_key;
    RETURN 'POSTED';
END $$;
