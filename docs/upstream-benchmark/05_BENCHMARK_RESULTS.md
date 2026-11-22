# 05 — Benchmark results and runnable worklist

## Baseline freeze and controls

- Baseline `69b93d53fa1715a613299204500eb024d170c1a2`, tree `16e2ee2a6ec1a7060b69fbbe0d1d933e2c1ce082`. Archive SHA-256 `47430f00f36299fcf5cd6cde64bc88ab5a5ba05f3e15f3d95e7eec01e5e4d494` for `git archive --format=tar HEAD` at the frozen state. The worktree was clean before this run.
- Environment observed: macOS, Python 3.9.6 from `.venv`, Node 24.22.1, and JDK 21.0.13. Use `--baseline`/`--candidate` with the existing isolated configuration lock for comparable routing runs. Treat browser version, viewport, fonts, and structural versus pixel mode as distinct conditions.
- Full baseline validation passed for 17 skills and 267 unit tests. Baseline browser structural runner passed 39 checks for plain/React plus Next source checks. Two runs against the pre-existing Next build timed out before readiness. A fresh checkout of the pinned fixture, with dependencies installed without lifecycle scripts, built and passed all 14 Next structural checks. The audit includes no visual pixel comparison.
- Compare five local deterministic controls on the frozen baseline and patched working tree. Run each three times in fresh synthetic temp directories. The old phase simulator is a reference for the former evidence surface. It was never an execution engine. The candidate uses actual input and result artifact digests.

| Control | Expected behavior | Before | After |
| --- | --- | ---: | ---: |
| All paired trials blocked on one side | Report insufficient evidence | 0/3 | 3/3 |
| Scanner finding on a synthetic marker | Omit marker text while retaining finding | 0/3 | 3/3 |
| Scanner text exceeds its byte limit | Surface a coverage limitation | 0/3 | 3/3 |
| No phase receipt | Keep dependent phase waiting | 0/3 | 3/3 |
| Input changes after a recorded check | Mark phase stale and hold dependents | 0/3 | 3/3 |

The controls are local behavior checks. They measure new guard behavior on fixed inputs. They do not measure model quality, attack resistance, latency or accuracy versus competitors.

## Observed model routing

Isolation preflight passed for these runs. Codex CLI used `gpt-6.2-sol` at `medium` effort. A/A ran the frozen baseline in both slots on `diagnose-only` and matched **6/6**. The paired A/B covered `diagnose-only`, `multi-module-migration`, and `third-party-skill-review`, with three repeats per case. **Baseline 9/9, candidate 9/9, zero blocked, and zero observed changes in exact-match outcome.** The candidate was the frozen baseline plus the two modified skill entries and the new phase reference. Patch SHA-256 `798795ec9e56fdbf0d193c194319976cacd734ae5806759a7fa4c7606fea23db`.

These were existing routing corpus cases. They tested route classifications and the user's scope, without executing the software tasks, loading an upstream bundle or measuring tool effects. Raw sanitized reports were retained in the separate local reference workspace. Use [the isolated routing runner](../../scripts/run_enhancement_benchmark.py) with the case IDs, model, effort and baseline specified above. A/B output includes both variants in a single JSON and may be passed in both input slots of the [comparator](../../scripts/compare_enhancement_results.py).

## Task benchmark worklist

For each case, pin the task, source, model/effort, fixture, grader and permission profile. Preserve variants A (baseline), B (relevant reviewed upstream feature) and C (candidate). Reserve undisclosed holdout prompts and graders outside the writable model workspace. Alternate execution order, start with three runs per variant where practical, record blocked outcomes and report results per case. When B needs a different runtime or dependencies, record that as a separate comparison stratum. Use local disposable fixtures and approved isolated profiles. Exit the run when a preflight fails. The [follow-up](10_PARITY_FOLLOWUP.md) records instruction-level upstream comparisons within B05 and B07.

| ID | Task and independent oracle | Relevant upstream | Current evidence |
| --- | --- | --- | --- |
| B01 | Fix a failing behavior test. Hidden grader reruns original check plus unaffected behavior. | Superpowers, Ponytail | NOT_RUN under agent conditions |
| B02 | Diagnose a cross-module regression. Known causal check must distinguish two plausible hypotheses and preserve read-only scope. | Superpowers, HumanLayer | NOT_RUN |
| B03 | Review Spring Batch staging/posting and chunk size. Oracle checks restart, duplicate effects, counts and measured query/throughput under a fixed data generator. | Trail of Bits property-based design | NOT_RUN. No Gradle on PATH. |
| B04 | Review PostgreSQL integrity and query behavior. Transactional synthetic DB checks exact row set and controlled query plan. | Source graph and specification approaches | NOT_RUN. No PostgreSQL client on PATH. |
| B05 | Repair duplicate payment on retry. Oracle verifies same and conflicting keys, balanced ledger and independent crash/replay control. | Superpowers, Trail of Bits property-based design | PARTIALLY_VERIFIED. Isolated SQLite repair includes concurrent writers, conflicting payloads and rollback. Worker-process crash and production dialects remain outside the observed scope. |
| B06 | Implement a React approval and verify flow including cancel/retry, focus and exact record. Add blind paired product review. | Vercel, DevTools, Impeccable | PARTIALLY_VERIFIED. Existing browser fixtures only. |
| B07 | Trace arch with async queue and SQL. Golden edges have source paths, symbols, types and explicit unresolved edges. | Archify, Serena, Codegraph, Graphify | PARTIALLY_VERIFIED. Three instruction snapshots tied on two static source-edge cases. Async, dynamic targets and graph runtimes remain outside the observed scope. |
| B08 | Resume session with true, stale and foreign records. Oracle validates scope, expiry, useful recall and recovery on provider failure. | Engram, ai-memory, Hermes, Context Mode | PARTIALLY_VERIFIED. Existing local adapter/contract tests. |
| B09 | Ambiguous multilingual request. Compare appropriate clarification, safe partial work, accurate intent and effective support skills. | Matt Pocock Skills, Superpowers | PARTIALLY_VERIFIED. Three local routing cases above. Ambiguity holdout and cross-upstream comparison NOT_RUN. |
| B10 | Review an untrusted instruction bundle using synthetic benign markers. Oracle checks no source text reaches scanner reports and files outside the snapshot are not read. | Sentry, Repomix | VERIFIED for the stated local controls. No adversarial agent evaluation. |
| B11 | Interrupt a multi-phase task then resume with a changed dependency. Oracle checks stale proof and no out-of-order completion. | HumanLayer, Hermes | VERIFIED for local phase receipts. Host behavior NOT_RUN. |
| B12 | Lose a check or produce all-blocked results. Oracle requires honest evidence-level reporting and a bounded follow-up. | Promptfoo, Superpowers | VERIFIED for paired coverage and missing/stale check handling. Agent task NOT_RUN. |

Measure acceptance (passed requirements / scheduled applicable requirements), actual independent regressions, cause anchors, boundary violations, necessary and unnecessary questions, tool calls, recovery, and reviewer task success. Record token, elapsed time and cost only if observed, otherwise `null`. Baseline/candidate controls alone cannot determine whether any upstream is superior. Overall matched superiority remains **INSUFFICIENT_EVIDENCE**.

Reproduce all five controls with [run_local_upgrade_controls.py](../../scripts/run_local_upgrade_controls.py) from the repository with the audited baseline commit available. It loads only the three fixed, first-party baseline scripts from that revision and evaluates temporary synthetic files. Run individual tests with `python -m unittest discover -s tests -p 'test_phase_receipts.py' -v`, and use the same command with `test_security_scan_boundaries.py` and `test_enhancement_comparison.py` as patterns.
