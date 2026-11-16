# Review and simplification gate

## Review gate

Use the changed files and their direct consumers first. Check correctness, regression
risk, security, public contracts, error handling, transaction boundaries, tests, and
observability. Every blocker needs a source location, a plausible trigger, impact, and
confidence. Separate blocker, improvement, question, and not-verified.

Do not claim a defect from style preference. Do not rewrite unrelated code while
reviewing. For a high-consequence or large change, an independent read-only reviewer
may be useful; it is optional and never a default fan-out.

## Simplification gate

Ask whether the same invariants can be preserved with less code, state, dependency, or
network/build work. Remove only what is demonstrably unnecessary. Never simplify away
validation, authorization, transaction boundaries, reconciliation, audit records, or
safety checks. A smaller diff that weakens an invariant is a regression, not a cleanup.

## Risk-weighted TDD

For financial, authorization, retry, batch, or other high-consequence logic, express the
invariant as a failing test before risky implementation when technically feasible:
duplicate execution, partial failure, replay, rollback, rounding, stale input, or
concurrency. If RED/GREEN is not feasible, record why and provide equivalent acceptance
evidence. A simple visual change needs proportionate checks, not TDD ceremony.
