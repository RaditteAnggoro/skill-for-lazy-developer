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

In the Lazy Developer repository, `scripts/verify_spec_traceability.py SPEC TEST_SOURCE`
checks references only. For execution evidence, generate a fresh JUnit XML report with
the project's normal test runner. Create a JSON object such as
`{"REQ-101":["approval.journey::test_selected_rows_change"]}`. Include every requirement
ID in the spec; use the JUnit `classname::name` of each relevant testcase, or `name` if
`classname` is absent. Verify that those tests actually assert the requirement.

```sh
python scripts/verify_spec_traceability.py spec.md \
  --assertion-map assertions.json --junit junit.xml --json
```

Missing, skipped, or failed mapped tests prevent a passing result. Tie the report to
the revision and command used to produce it. For continuation, bind the inputs and
report to the phase receipt. The JUnit reader checks recorded outcomes, while the test
owner remains responsible for the assertion's scope and the report's provenance.
