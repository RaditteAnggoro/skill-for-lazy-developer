---
name: spec-to-code-verification
description: "Compare testable requirements with implementation and test evidence, producing a requirement-to-evidence matrix. Use for a deliberate specification audit, not for every ordinary code edit."
---

# Specification-to-Code Verification

Determine whether the implementation actually satisfies the written requirements. This
is a verification workflow; it produces findings unless implementation is also requested.

## Establish the requirement set

Locate the authoritative specification, acceptance criteria, or contract. Record its
version and scope. Split compound requirements into individually testable statements
with stable IDs. Separate must-have requirements from examples, non-goals, and unresolved
questions.

Do not invent missing requirements. If the spec is ambiguous or contradictory, report
the ambiguity and route product decisions to `feature-discovery`.

## Trace to evidence

For each requirement, collect:

- implementation location or external contract;
- automated test or executable check;
- observed result and environment;
- gaps, partial coverage, and assumptions.

Use code search and existing tests; do not count a test name as proof without checking
what it asserts. Distinguish unit, integration, contract, browser, and manual evidence.
A requirement with no test can still be verified manually, but label the method and
residual risk.

Read [traceability-matrix.md](references/traceability-matrix.md) for the output format.

## Report and verify fixes

Report pass, fail, partial, untested, and out-of-scope requirements. Include orphan tests
that do not map to a requirement only when they create maintenance risk. If implementation
is authorized, make the smallest fix and rerun the affected evidence. Never claim full
specification compliance from a green build alone.
