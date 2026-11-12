# Synthetic Java repayment fixture

This plain Java fixture intentionally repeats a posting when an event is replayed.
It uses no Spring, database, external network, or production data. The benchmark task
is to prevent duplicate effects without discarding distinct events or unbalancing the
ledger. The baseline verifier is expected to fail on replay. This is not a Spring Batch
or production banking integration test.
