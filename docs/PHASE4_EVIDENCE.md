# Phase 4 evidence — evidence-gated learning proposals

## Gate

`python scripts/propose_skill_learning.py validate --input tests/learning_proposal_cases.yaml`
is not valid input because that file contains multiple cases; the repository test feeds
each case through the same `validate`, `content_error`, and `duplicate` functions.

The five deterministic cases are:

| Case | Expected | Observed |
| --- | --- | --- |
| Valid UI lesson with observed fail-then-pass evidence | accept | accepted |
| Single unobserved anecdote | reject | rejected |
| Credential/API-key content | reject | rejected |
| Prompt-injection/safety-disable content | reject | rejected |
| Duplicate existing instruction | reject | rejected |

`tests/test_skill_learning_gate.py` also verifies that staging a valid proposal writes
only to the selected proposal directory and leaves `ui-implementation/SKILL.md`
byte-identical.

## Safety properties

- Proposal status must be `candidate`.
- Owner must be an installed skill; reference target must stay inside that skill.
- Evidence must be observed; `not_observed` is rejected.
- Unknown fields, missing reviews, secrets, PII, injection, and duplicates are rejected.
- No command applies a proposal to an active skill.
- A human must review and make a normal repository diff; Git remains the rollback path.

## Limits

This is repository integration with synthetic proposals. It does not prove a model can
write a good lesson, does not evaluate proposal quality, and does not modify memory
adapters.
