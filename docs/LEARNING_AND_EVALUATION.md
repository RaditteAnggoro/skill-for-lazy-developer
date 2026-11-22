# Learning proposals and evaluation

## Memory vs learning

Memory stores bounded project facts/history under the existing Engram contract. A skill
retains a reusable procedure and loads only when relevant. A memory record is never
automatically executable instruction.

## Proposal pipeline

```text
verified task evidence
  -> candidate rule + conditions + limitations
  -> privacy/security scan and duplicate check
  -> local proposal (not active SKILL.md)
  -> regression/routing/task evaluation
  -> human review of diff and rollback
  -> normal repository edit if accepted
```

Use [the schema](schemas/skill_learning_proposal.schema.json) and
`python scripts/propose_skill_learning.py validate/propose`. Sensitive material,
unobserved anecdotes, prompt injection, duplicate rules, and unverified claims are
rejected. The tool never edits an active skill.

Proposal IDs are write-once. Use a new ID for edited evidence. To ground the claimed
outcomes, add `receipts` in execution order to an evidence item. Each entry contains
the `run_id` and `sha256` from the local phase-check recorder, and `case_id` equals
the declared check ID. Run `python scripts/propose_skill_learning.py verify-evidence
--input proposal.yaml --artifacts /path/to/phase-artifacts`. It validates the bound
outcomes and requires the same check command for a fail-then-pass pair. Staging alone
still permits proposed evidence that a reviewer has yet to verify. Approval and any
active-skill change remain manual.

## Evaluation levels

| Level | Evidence | Not proven |
| --- | --- | --- |
| STATIC | schema, links, deterministic wrappers, policy text | agent behavior |
| SIMULATED | decision tables and role/learning fixtures | real host dispatch |
| REPOSITORY_INTEGRATION | scripts/tests on synthetic fixtures | production |
| HOST_INTEGRATION | actual Codex/Claude/DSH session | all hosts |
| REAL_USER_JOURNEY | authorized browser/DB test | guarantee elsewhere |

Label every result. A green build does not prove a role was dispatched or a browser
journey occurred. Host unavailable is `NOT_RUN`/`UNVERIFIED`, never a synthetic pass.

## Metrics

Track correctness, safe-scope compliance, evidence truthfulness, regression recall,
review precision, routing/delegation precision, unnecessary delegation, tool
duplication, latency, total tokens, local resource use, privacy incidents, proposal
acceptance, and cross-host parity. Collect a frozen baseline first; do not invent
percentage improvements.
