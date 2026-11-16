# Enhancement v3 baseline

Baseline selected on 2026-11-11: commit `5b6f66debd23681d1b057e6dff9bfcdfb08d7c7f`
plus the pre-existing tracked changes in `AGENTS.md`, `docs/CODEX_ADAPTER_EVIDENCE.md`,
`integrations/codex/memory_runtime.py`, and `tests/test_codex_adapter.py`. The user
explicitly chose to include those changes. The combined binary Git diff had SHA-256
`d5675624188ab21c478d0eb4643019650af68d5f08b29e9da5dad51e5b24c141` before the
subsequently approved change to the local AGENTS.md phase limit. This hash identifies
content but does not itself preserve it. After the user approved aligning the local
phase limit, an ignored local patch was saved at
`.agents/artifacts/enhancement-v3/baseline-tracked.patch` with SHA-256
`501db75a5d27532d153852d0abdd32c18da4f1d18a6bfe369375507c4792fd6a`. It can be
applied to the baseline commit in an isolated checkout; it is not distributed or
committed. Untracked `.engram` and the AGENTS backup are private/local and excluded.

Before skill changes, `scripts/validate_skills.py` validated 17 skills and
`python -m unittest discover -s tests -q` passed 176 tests on the dirty working tree.
Python 3.9.6, Node 24.22.1, npm 11.19.1 and Codex CLI 0.167.0 were observed locally.
A single read-only model routing trial for `browser-journey-review` passed; it is not
an A/B benchmark. Host, model effort, network policy and fixture revisions must
be recorded in each comparable run. No human blind review has been performed.

The existing Phase 6 fixture checks passed 8/8. The existing token benchmark passed
eight context-retention fixtures; it does not measure live agent cost or quality.
An A/A smoke test of the new routing runner passed all six trials for one case with
the same snapshot on both sides; it checks the harness, not an improvement. A broader
three-trial routing baseline was completed using the restricted profile: 136 of 156
trials matched the locked expected route, 20 did not, and none were blocked. This is
87.18% per trial, before any human adjudication of the expectations. The raw report,
including all differences, is saved locally under
`.agents/artifacts/enhancement-v3/baseline-hardened/`. Neither the backend/UI task
corpus nor blind reviewer baseline is complete. One earlier isolated
baseline batch stopped after three blocked CLI invocations; a later targeted repeat
passed three of three, so the earlier failure's cause remains unconfirmed.

After reviewing two newly added UI cases, the user approved correcting their expected
supporting skills to reflect the existing UI and verification contract. The original
corpus and 136/156 report remain unchanged in local artifacts. A separate derived
report re-scored only those two support expectations using recorded routing choices,
preserved all other errors, and reported 138/156. After clarifying that browser journey
is a subsequent phase, a second derived report uses verification as the implementation
phase's support and reports 137/156. Both are derived results, not reruns; the original
report and corpus remain intact, and hashes and approved changes are recorded.
The runner does not retain model response text; a wording-grader failure by itself
cannot support a conclusion about the naturalness of the response without further review.
The baseline routing batch shares this host with unit tests and UI fixture builds;
its wall times are descriptive and cannot be used for a controlled latency comparison.
The first locked routing run was stopped after an isolation concern: its read-only
sandbox did not prevent reading outside the temporary workspace, and model tool logs
were not retained. A live model successfully read a synthetic outside canary in that
mode. Whether any outside files were accessed in earlier trials is unknown; the prior
report's statement that only workspace instructions were exposed is too broad.
Those earlier trials also inherited the parent process environment; whether any
environment variables were inspected is unknown. No such access has been established.

A custom profile was then checked with a synthetic canary: a live model could read a
file inside the workspace but was denied an outside file. A local shell preflight also
confirmed denial for an outside file, a symlink to it, and a synthetic local TCP listener.
The runner now fails closed when this preflight fails. These checks cover the tested
CLI/host and local shell paths; they do not prove that every connector, external tool,
or future environment is isolated. See the official [Codex permission-profile
documentation](https://developers.openai.com/codex/permissions).
The runner now forwards only an allowlist of ordinary host settings and checks that a
synthetic secret variable is not forwarded. Provider API keys and arbitrary environment
variables are excluded; custom authentication that relies on those variables may be blocked.
For evaluation subprocesses it disables hooks, plugins, apps, browser use, web search,
and automatic skill-MCP installation without changing user configuration. A restricted
single-case model smoke test passed. These controls do not establish behavior for other
hosts or unseen tool surfaces.

The tracked baseline plus the selected local patch was also checked in a temporary
checkout with the installed Chrome: 35 plain/React and 12 Next fixture checks passed,
including the fixture screenshot comparisons. Dependencies were installed with npm
lifecycle scripts disabled and Next telemetry disabled. Logs and screenshots are local
under `.agents/artifacts/enhancement-v3/baseline-ui/`. These three fixture stacks are
not the eight-page evaluation corpus and no human blind review has been performed.

One additional synthetic SQLite repayment repair task was run three times in a
restricted writable workspace. Its independently copied verifier passed twice; the
third model run timed out after 300 seconds and is `blocked`. This single fixture is
not the required multi-task backend corpus and does not establish Java, production
banking, external settlement, or concurrency safety. The raw trial summary is local at
`.agents/artifacts/enhancement-v3/repayment-baseline.json`.

An additional isolated, read-only impact evaluation used eight synthetic Python
source-file questions with three trials each. The baseline selected exactly the
fixture's expected files in 24/24 trials; the raw results are local at
`.agents/artifacts/enhancement-v3/impact-baseline-fixed.json`. This is a small,
controlled file-selection fixture, not evidence of Java/Spring coverage, runtime
correctness, real-repository accuracy, cited source anchors, or an improvement over the
baseline. An earlier
attempt was blocked by an unsupported response-schema keyword; its blocked results
are retained separately and were not counted as failures or successes.

A frozen provisional candidate (`candidate-sequential.patch`, SHA-256
`5d3f2e187004af3a9a456519017bb67288b9c1f718081c2f2d12cde0720abb32`)
also matched 24/24 on the same fixture, with matching recorded runner, model, host,
permission profile, environment, and corpus hashes. Its raw report is local at
`.agents/artifacts/enhancement-v3/impact-candidate-sequential.json`. This candidate
snapshot predates a later change to the tool-selection reference; the result applies
to that snapshot only. The equal scores show no measured difference on this small
fixture and do not establish general equivalence or quality.

## Measurement design

Freeze identical prompts, synthetic fixtures, environment, model/effort and tools for
baseline and candidate; use independent isolated snapshots and at least three trials
per task. Preserve pass/fail/blocked and actual evidence per trial. Separate deterministic
checks from blinded human review. Record unavailable token, cost, or telemetry fields as
null, not zero. The proposed metrics and gates are in the specification; no numeric
improvement is claimed until comparable runs are available. Data must be synthetic and
sensitive traces redacted. Do not run upstream installers or transmit private sources.
