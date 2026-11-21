# Phase receipts for local continuation

Use receipts when a multi-phase task must survive interruption or review across
sessions. In this repository, `scripts/verify_phase_receipts.py` consumes an ordinary
phase plan extended with `inputs` and `required_checks` on each phase. Use precise
workspace-relative input files (such as an API contract, changed source and the check
definition) and stable check IDs. Freeze the plan before collecting evidence.

```yaml
inputs: [src/approval.py, tests/test_approval.py]
required_checks: [approval-regression]
```

Get the canonical plan fingerprint with `python scripts/verify_phase_receipts.py
plan.yaml --plan-digest`. The JSON bundle has `version: 1`, `plan_sha256`, and a
`phases` array. For each observed phase provide `id`, `input_sha256` (file name to
SHA-256), and `checks` (check ID to observation). Record a passing observation only
from the required check on those exact inputs. It needs `outcome: passed`, `path` to
the output under the artifacts directory, and `sha256` of that artifact. Failed,
blocked, and unrun checks use `failed`, `blocked`, and `not_run` respectively. Keep
artifacts local and avoid storing credentials, private payloads and full transcripts.

```sh
python scripts/verify_phase_receipts.py plan.yaml receipts.json \
  --workspace . --artifacts .agents/artifacts/my-task
```

The verifier reads only the declared files and derives completion, readiness,
waiting, blocked or stale status. A dependent phase waits until its predecessors
have passing, current receipts. Exit status 0 means every phase has complete
receipts, 1 means valid but incomplete, and 2 means malformed input. A plan change
requires a new digest. Re-run checks affected by changed inputs and retain the old
records as historical evidence. Use the observed outputs and provenance to judge
whether the required check really ran. A digest verifies current contents, while
the observation producer remains a trust boundary. The optional script does not
execute commands, grant authority, or constrain host tool use.
