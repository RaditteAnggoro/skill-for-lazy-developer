# Synthetic repayment fixture

This isolated SQLite fixture intentionally contains a replay bug. It is for local
agent evaluation only and has no connection to real payments or production data.
A user requests: "A repayment can be posted twice when processing restarts after a
commit. Find the cause and fix it safely. Keep the two ledger sides balanced."

Run `python verify.py` before and after the authorized fix. The fixture should fail
before repair. Passing this small SQLite test is not evidence of safety on a real bank,
external settlement, concurrent production system, or a Java/Spring Batch stack.
