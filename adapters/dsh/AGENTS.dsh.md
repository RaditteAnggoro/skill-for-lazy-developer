## DSH routing calibration

These rules supplement the shared companion instructions on DeepSeek Harness.

- Always return a nonempty `user_message`; never use `null`. A short sentence is
  enough for an automatic, read-only route.
- `adaptive-workflow` is the router, not a supporting workflow. Supporting entries
  must be peer workflows that perform the work.
- A browser-visible failure uses `browser-diagnostics` as primary and
  `systematic-debugging` as support. A browser performance or evidence request with
  no failure uses `browser-diagnostics` only.
- Do not add `verification-before-completion` to a documentation-only edit or a
  release assessment. `release-readiness` owns outstanding release evidence.
- A request to check whether an existing change fixes a reported bug uses
  `verification-before-completion` only. Add `systematic-debugging` only when the user
  asks to diagnose or find a cause.
- When `research-plan-implement` is primary for a substantial migration, do not add
  `lean-senior-engineering`; the primary already owns implementation. Add only a
  distinct responsibility such as verification.
- When a planning request already states the decision dimensions, produce the plan
  and a recommended default. Ask only when a remaining choice materially changes the
  outcome.
- For casual Indonesian, use a natural informal marker such as `aku`, `kita`, `kamu`,
  or `bisa`; do not shift to a formal “Saya akan ...” register.
