UPDATE financial_stage SET state = 'POSTED', owner_id = NULL, lease_until = NULL
WHERE event_key = :event_key;
