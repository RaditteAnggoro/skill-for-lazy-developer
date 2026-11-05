# Requirement-to-evidence matrix

| Requirement | Testable statement | Implementation | Evidence | Status | Residual risk |
| --- | --- | --- | --- | --- | --- |
| REQ-001 |  | file/function or contract | test/manual check and result | pass/fail/partial/untested |  |

## Rules

- Use stable requirement IDs from the source; do not renumber silently.
- A test name alone is not evidence; inspect its assertion.
- Record the environment and data fixture for manual evidence.
- Mark requirements outside the declared scope as out of scope, not passing.
- List contradictory or unverifiable requirements separately.
