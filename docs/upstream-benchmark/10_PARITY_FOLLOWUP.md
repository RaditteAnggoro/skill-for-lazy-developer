# 10 — Capability follow-up

Reviewed 2026-11-22 against Lazy Developer baseline `47d0976`. The candidate
updates existing skills, verification scripts and adapters. The skill roster
remains at 17. The [source inventory](01_SOURCE_INVENTORY.md) records the pinned
upstream versions and the [adoption register](08_LICENSE_SECURITY_PROVENANCE.md)
covers licensing.

## Ten weaknesses and current evidence

| # | Weakness | Implemented and exercised | Remaining evidence |
| --- | --- | --- | --- |
| 1 | Simulated completion | The local recorder executes explicit argv and attests a typed exit status, check and plan digest. The verifier checks the matching receipt across processes. | Host authorization and hosted CI provenance. |
| 2 | Phase handoff | Missing, stale and mismatched evidence prevents a dependent phase from completing. An artifact carrying the wrong check is rejected even after its checksum is updated. | Observation from a hosted run resumed in a separate session. |
| 3 | Security and privacy | Scanner findings retain coverage without raw snippets. Clean source builds take file names and contents from the committed snapshot. An ignored draft and an index-hidden working-tree edit both stay out of the test archive. | Human review of manually chosen source and trust boundaries. |
| 4 | Benchmark reliability | Isolated A/B and A/B/C comparisons report per-arm denominators. Repayment needs at least three fully graded matched rounds to satisfy the fixture comparison gate. | More task families and an independent review sample. |
| 5 | Engineering intelligence | The grader now requires exact source file, line, caller and target on an authorization chain and a SQL reference. The architecture skill marks static evidence explicitly. | Asynchronous and dynamic edges, Java/Spring and optional index runtime. |
| 6 | Specification verification | JUnit execution mode requires each mapped assertion to run and pass. The earlier browser pilot maps two requirements to three observed assertions. | Additional specifications and CI-produced evidence. |
| 7 | Agent orchestration | Four role contracts render deterministically for Codex and Claude. Two isolated Codex canaries produced no child-role evidence. Claude CLI reported no login. | Positive role, scope and timeout/fallback observations in real hosts. |
| 8 | Memory and learning | New records bind recall to the project root. Adapter tests reject stale or foreign records and untyped command success. A synthetic Codex CLI check proved exact command matching against a typed host event. Learning proposals are write-once and can verify receipt-linked runs. | Installed hook transcript and provider migration for older unscoped records. |
| 9 | UI, browser and MCP | Real Chrome covers rejection, retry, narrow reflow and keyboard use in plain, React and Next.js. Negative controls catch a no-op rejection and missing visual baseline. A local Chrome DevTools MCP call inspected the accessibility tree, console and network and observed the selected row change. | Additional domains, blind review and pinned pixel comparisons. |
| 10 | Transaction and portable evidence | The SQLite holdout checks concurrent writers, retry after database reopen, payload conflicts, and rollback/retry when the second write fails. The portable import journal recovers partial writes and preserves later edits. | Worker-process crash, PostgreSQL/Spring Batch/Oracle behavior, scale tests and manual restoration of pre-journal backups. |

## Matched model experiments

Each experiment uses synthetic data under an observed local isolation preflight.
The model gets the same task and fixture across arms. Grading of the repayment
holdout occurs in a separate sandbox after the model turn. Scope is limited to
the cited instruction files and fixture behaviors. Host dispatch and product
integration use different evidence.

| Experiment | Baseline | Upstream | Candidate | Result |
| --- | ---: | ---: | ---: | --- |
| Three routing cases, three repeats each | 9/9 | — | 9/9 | Exact scope and skill classification in the sampled cases. |
| Two static source-edge cases, three repeats each | 6/6 | 6/6 Archify | 6/6 | Equal precision and recall (1.0) on this fixture. |
| SQLite repair including the holdout, initial run plus extra round with 120-second timeout | 4/4 | 2/4 Superpowers, 2 blocked | 3/4, 1 blocked | All arms pass both fully graded rounds. There was one upstream timeout and two CLI failures of unknown cause. |
| SQLite recheck with 180-second timeout | 3/3 | 2/3 Superpowers, 1 timeout | 3/3 | All arms pass both fully graded rounds. The three-round gate remains `insufficient_evidence`. |

Routing uses GPT-6.2 Sol at low effort on `diagnose-only`,
`indonesian-failing-test`, and `transfer-idempotency-review`. Source-edge cases
use the same model and effort, with Archify's instructions at `8509a3d` and no
Archify index or renderer. The repayment arms use the same model at medium effort.
The upstream arm reads two Superpowers skills at `22f0b46`, for debugging and
completion verification. The Lazy Developer arms also read the transaction skill.
The timeout profiles have separate denominators. The evidence establishes
fixture-specific parity for source edges and equal observed outcomes in the
complete SQLite rounds. Broader parity and superiority across the upstream
catalog remain unestablished.

The [repayment comparator](../../scripts/run_repayment_comparison.py) accepts the
pinned public clone as `--upstream`, with `--model gpt-6.2-sol --effort medium`
and a new `--output` under the local artifacts directory. Its report captures
fixture, instruction, grader and permission-profile digests. The
[source-edge evaluator](../../scripts/run_impact_evals.py) uses the two new edge
cases in the [corpus](../../tests/enhancement/impact_cases.yaml). Raw model output
and private project data are outside the retained benchmark artifacts.

## Repository verification

- Validation passed for 17 skills, both sets of role wrappers, 290 unit tests,
  and the DSH adapter lifecycle. The UI runners add 21 assertions across the three
  fixture implementations. All 74 structural checks passed on fresh builds from
  the pinned lockfiles. Structural mode captures screenshots and leaves pixel
  comparisons to a pinned visual run.
- The DevTools observation used a dedicated browser context and a loopback server.
  Reloading the fixture after adding an inline icon yielded an HTTP 200 and no
  warning or error messages in the console.
- The clean source archive contained 319 entries and passed checksum, ZIP integrity
  and committed-path checks. The portable pack manifest verified 17 skills and
  four opt-in roles. Hosted validation depends on a run against the published revision.

See the [remaining roadmap](07_REMAINING_ROADMAP.md) for the evidence required
to close the open rows.

## P0 and P1 delivery

- Codex CLI 0.167.0 supplied typed command completions to the installed `Stop`
  hook. The adapter accepts the exact command from the current turn. An earlier
  turn and command output implying success both fail the regression test.
- Engram 3.6.2 retained complete records across recall, isolated two roots called
  `demo`, and deleted only the confirmed observation in the synthetic project.
  Existing display-name buckets can be reviewed before explicitly re-saving facts.
- The CI smoke test records a receipt for the orchestration corpus, carries it as
  short-lived synthetic metadata, and resumes independently on a second runner.
- Chrome now checks 60 assertions in the plain, React and source-check runner,
  including seven inventory checks in structural mode. The separate Next runner
  covers 21 assertions. A blind panel and pinned pixel comparisons remain separate.
- The batch worker test causes abrupt process exits after the first posting and
  just after a chunk commit. A disposable local run reconciled 100,000 staging
  events and 200,000 postings through restart and replay. This measures SQLite.
- A read-only B02 scenario tests whether the diagnosis localizes fractional amount
  loss to the conversion and excludes the downstream posting function. GPT-6.2
  Sol at low effort scored **3/3** on the baseline and **3/3** on the candidate
  under the same synthetic fixture and exact-anchor grader. No upstream arm
  participated in that run.
