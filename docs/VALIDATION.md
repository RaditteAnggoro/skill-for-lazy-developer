# Validation scope

## Automated checks

Run `python scripts/validate_skills.py` after installing `requirements-dev.txt`.

The validator checks:

- Each skill has YAML frontmatter, a valid directory-matching name, a concise nonempty description, and a nonempty body.
- Skill metadata has no duplicate keys.
- UI metadata has a display name, a correctly sized description, a natural default
  prompt, and a valid optional implicit-invocation policy.
- Linked local files exist, stay inside the repository, and use portable links.
- GitHub workflow and issue-form YAML can be parsed.
- Routing cases reference installed skills, keep automatic chains small, avoid
  explicit skill-name syntax, and cover automatic, choice, and question interactions.

External URLs, Markdown anchors, model decisions, and application runtime behaviour are outside structural validation.

Run `python -m unittest discover -s tests -v` to test the validator and archive builder, including rejection of invalid metadata, missing references, and paths outside the repository.

The initial repository preparation passed 18 tooling tests locally on Python 3.9.6.
The original eight skills passed structure and local-link validation, and the
generated ZIP passed its integrity check. Hosted GitHub Actions had not yet run at
that point; the workflow is configured for Python 3.9 and 3.13.

The adaptive-routing increment adds a ninth skill and a natural-language routing
corpus in `tests/routing_cases.yaml`. Unit tests establish policy consistency and
fixture validity. They do not prove that every model, version, or surrounding prompt
will make the same semantic routing decision.

## Workflow trial

The initial pack was exercised on 2026-10-28 using a disposable Python pagination fixture. An independent agent read the implementation, debugging, and verification skills and received a request to fix a failing first-page test.

Observed results:

| Stage | Outcome |
| --- | --- |
| Existing baseline | 2 tests, first-page test failed |
| Expanded regression cases before fix | 6 tests, 4 failed |
| Focused offset fix | One implementation line changed |
| Verification after fix | 6 tests passed |

A separate independent file review examined all eight original skills and the initial
documentation. The resulting refinements clarified reuse of existing regression
tests, diagnosis-only source boundaries, and saved-artifact scope.

This trial does not establish behaviour across all models, codebases, or every workflow. Browser access, actual release execution, and hosted GitHub CI were not exercised by that trial. Report new evaluation results with the prompt, environment, expected behaviour, and observed evidence.

## Adaptive-routing trial

On 2026-11-04, four natural-language routing cases were run independently with
Codex CLI `0.166.0-alpha.5.1`, model `gpt-6.1-sol`, a read-only sandbox, the consuming
`AGENTS.md` snippet, and all nine skills copied into disposable directories. The
trials requested a route only; they did not execute or modify a project.

| Task shape | Expected interaction | Observed route |
| --- | --- | --- |
| Failing invoice unit test, fix requested | Automatic | `systematic-debugging` → `verification-before-completion` |
| “Improve the login experience” | Choice | Three outcome-based choices led by `feature-discovery` |
| Read-only campaign data-flow trace | Automatic | `architecture-map` only |
| Blank dashboard after browser refresh, fix requested | Automatic | `systematic-debugging` + `browser-diagnostics` → `verification-before-completion` |

All four successful reruns matched the requested interaction mode, kept the selected
set to three focused workflows or fewer, and preserved read-only boundaries. The
first harness attempt did not run because its strict output schema used an unsupported
`uniqueItems` keyword; the schema was corrected and the cases were rerun. That failed
harness attempt is not counted as a routing pass.

Final local maintenance checks validated all nine skills and local links, passed 26
unit tests, and built a reproducible 55-file release archive whose SHA-256 checksum
was verified. The workflow illustration was rendered in a local Chromium browser and
inspected at its native 1280 × 640 viewport.

These results establish only the observed routing behaviour for the stated CLI,
model, prompts, and instructions. They do not guarantee identical selection across
future models or additional repository context; `tests/routing_cases.yaml` is the
regression corpus to extend when a real routing miss is reported.

## Version 2 Phase 0 gate

On 2026-11-04, Phase 0 added a machine-checked capability and phase-ownership record,
expanded the routing corpus from 13 to 20 natural-language cases, and added a
repeatable read-only model evaluation runner.

The corpus covers every installed workflow as a primary route and includes direct,
contextual, and negative-control requests. Ambiguous feature requests accept either
an outcome choice or one blocking question, but never automatic implementation.

The first expanded model run passed 18 of 20 cases. Review found that one browser
fixture contradicted the router's documented ownership and one missing-context prompt
contained release-readiness wording. After correcting those fixtures, a full run
exposed that two deliberately ambiguous feature prompts can validly use either a
choice or a single question. The evaluator was narrowed to accept only those two
interactive forms for those declared cases; `automatic` remains a failure.

Final observed evidence:

| Check | Result |
| --- | --- |
| Repository validator | 9 skills and local links passed |
| Unit tests | 40 passed |
| Final model-routing corpus | 20 passed, 0 failed |
| Repeated ambiguous login case | 3 passed, 0 failed |
| Repeated ambiguous dashboard case | 3 passed, 0 failed |
| Model trial permissions | Ephemeral session, read-only sandbox, disposable workspace |

The model trials used Codex CLI `0.166.0-alpha.6`, model `gpt-6.1-sol`, and structured
output constrained by `tests/routing_result.schema.json`. The runner scores
interaction, primary workflow, and supporting workflows. At the Phase 0 gate it did
not yet grade `user_message` wording or execute the requested software task. Final
maintenance checks used Python `3.9.6`, built a reproducible 61-file archive, verified
its SHA-256 checksum, and tested the ZIP contents. Phase 1 remained blocked at that
historical gate.

## Version 2 Phase 1 gate

On 2026-11-05, Phase 1 added a bounded companion policy and message-quality grading.
The policy treats the interaction as help from an approachable friend rather than a
formal support desk, matches casual Indonesian and English register, welcomes basic
questions, and avoids redundant permission questions. It remains explicit about
uncertainty, tool access, identity, memory, and observed evidence.

The interaction corpus added four cases for Indonesian continuation, casual source
explanation, informal feature discussion, and payment-integrity pushback. Message
grading rejects canned or formal service language, excessive length, unwanted
questions on clear tasks, missing questions when context blocks progress, and unsafe
agreement to remove duplicate-payment protection.

Evaluation was iterative rather than treated as a one-shot score:

- The targeted companion and safety set passed 6 of 6 cases.
- The first full run passed 22 of 24. It exposed an underspecified-request boundary
  and a redundant implementation workflow added to a debugging chain. The router was
  clarified, then both cases passed three repeated trials each (6 of 6).
- A later full run produced correct natural messages but exposed two overly narrow
  fixtures: casual “aku” was not accepted as friendly language, and a reference to an
  absent prior issue was still expected to guess a debugging target. The fixtures
  were corrected to reflect the documented behaviour.
- After the always-on policy was compacted, the complete final-state corpus was run
  again and passed 24 of 24 cases.

Final observed evidence:

| Check | Result |
| --- | --- |
| Repository validator | 9 skills, UI metadata, GitHub YAML, and local links passed |
| Unit tests | 48 passed |
| Final routing and interaction corpus | 24 passed, 0 failed |
| Repeated previously unstable cases | 6 passed, 0 failed |
| Companion policy budget | 199 words; complete consuming snippet 637 words |
| Model trial permissions | Ephemeral session, read-only sandbox, disposable workspace |

The final model trials used Codex CLI `0.166.0-alpha.6` and model `gpt-6.1-sol`.
Local maintenance used Python `3.9.6` and built a reproducible 61-file release archive.
The corpus evaluates routing and the short user-facing routing message; it does not
execute the described application task or guarantee identical phrasing from future
models. Phase 1 is complete. At that historical gate, Phase 2 remained blocked until
the memory contract and provider bake-off had their own passing evidence.

## Version 2 Phase 2 gate

On 2026-11-05, Phase 2 added a provider-neutral memory record and bundle contract, a
local-only bake-off runner, a nine-record / twelve-query corpus, and contract tests.
The contract rejects secrets, customer-data patterns, raw oversized content, broken
supersession links, duplicate active topics, wrong-scope records, untrusted active
records, and unsupported verified inference. It demotes records whose repository
anchors no longer exist and keeps stale or superseded records out of automatic
context.

The bake-off compared ai-memory 3.4.0 and Engram 3.6.2 using official release binaries
with verified checksums, disposable home/project/data directories, loopback-only
services, no LLM or cloud configuration, and the same corpus. Both providers passed:

| Check | ai-memory | Engram |
| --- | --- | --- |
| Recall after contract filtering | 12 / 12 | 12 / 12 |
| Stale leaks | 0 | 0 |
| Cross-project leaks | 0 | 0 |
| Privacy canary rejected / absent from store | yes | yes |
| Delete then restore | pass | pass |
| Restart then recall | pass | pass |
| Portable import | no | yes |

Engram is selected for the first Phase 3 adapter on observed setup/query overhead and
portable import. The full measurements, the exact versions, and the limits are in
[`docs/V2_PHASE2_EVIDENCE.md`](V2_PHASE2_EVIDENCE.md).

This trial does **not** establish automatic capture, lifecycle-hook behaviour, Codex
integration, concurrency safety, crash recovery, network-loss behaviour, or fail-open
operation. Status and trust filtering was adapter-enforced; the providers do not
natively own the contract schema. The privacy probe was rejected before provider
storage, so upstream secret scrubbing was not tested. At that gate Phase 3 remained
blocked.

Final local maintenance checks validated all nine skills and local links, passed 75
unit tests, and built a reproducible 71-file archive whose ZIP integrity was checked.
The new memory contract, schema, benchmark, and evidence files are included in that
archive. The provider binaries and provider data stayed in ignored local artifacts.

## DSH adapter standard verification

On 2026-11-05, a DeepSeek Harness adapter was added without opening Phase 3. The
standard target covered skill discovery, the full routing corpus, read-only workspace
snapshots, memory lifecycle, privacy, provider failure, and bundle uninstall—not a
three-prompt smoke test.

The DSH profile mounted the native skill, instruction, and tool plugins. It reported
all nine skill names. The full `tests/routing_cases.yaml` corpus passed **24/24** with
DeepSeek `deepseek-flash`; the runner hashes the disposable workspace before and after
each case, so a source edit fails the read-only check. The initial run passed 17/24 and
exposed host-specific routing differences; the DSH overlay and targeted reruns are
recorded in [`docs/DSH_ADAPTER_EVIDENCE.md`](DSH_ADAPTER_EVIDENCE.md).

The Engram MCP verifier passed all nine checks: bundle manifest, save/search, context,
restart, delete, cross-project isolation, privacy guard, and fail-open configuration.
The bundle lifecycle test passed four checks in a disposable profile: rows installed,
DSH started and answered with Engram absent, rows removed, and DSH still worked after
uninstall. The installer tests cover create, check, idempotent install, uninstall,
rollback, and preservation of unrelated `AGENTS.md` content.

Direct Engram MCP storage accepted the synthetic canary. The Host guard is therefore
required; its Node unit test rejects the canary and the bundle includes the guard row.
The live DSH model also refused to issue the canary write, so the end-to-end Host
denial was not observed. This distinction is recorded rather than presented as a
provider privacy pass.

Final current maintenance checks: validator passed for 9 skills and local links, 103
unit tests passed, and the reproducible archive contains 91 files with a verified
SHA-256 checksum. At that point Phase 3 was still blocked; it later completed with
the Codex and DSH slices described below.

## Phase 3 Codex vertical slice

On 2026-11-05, Phase 3 opened with a Codex-first scope. The adapter uses Codex
`SessionStart`, `UserPromptSubmit`, and `Stop` hooks to recall bounded Engram context,
handle explicit remember and project opt-out controls, and write a bounded handoff. It
is user-level, merge-safe, backed up, reversible, and fail-open.

The end-to-end run used Codex `0.166.0-alpha.6`, model `gpt-6.1-sol`, and Engram
`3.6.2` in a disposable `CODEX_HOME`, project, Engram store, and session. Six
end-to-end checks passed: recall, explicit remember, bounded handoff, missing-Engram
fail-open, project opt-out, and uninstall. Unit checks additionally cover privacy
skipping, idempotent installation, rollback, and preservation of unrelated hooks.

The installer does not trust hooks. The end-to-end test used
`--dangerously-bypass-hook-trust` because it is automated and disposable; normal users
must review the exact definitions once in Codex `/hooks`. The `Stop` handoff is stored
as conditional, and `forget` requires confirmation rather than silent deletion.

DSH now has a Host lifecycle plugin: `agent/pre-step` recall and controls, and
`agent/turn-stopping` handoff. Its Node lifecycle test passed. The first live attempts
failed with `TRANSPORT` because the injected context lacked a complete DSH message
identity and was added before the real prompt. After fixing the identity and adding
recall during the pre-step, a live disposable DSH run passed recall, remember,
handoff, opt-out, fail-open, and uninstall. Claude Code now has a user-level
`settings.json` adapter using the same runtime; settings merge, hook shapes, controls,
fail-open, idempotence, rollback, and uninstall passed, but no Claude binary or
authenticated session was available for a live model run.

The Phase 3 gate is complete with verification `verified-with-deferred-claude`.
Codex has live transcript-backed verified handoff and confirmed forget; DSH has live
lifecycle and confirmed forget; Claude live verification is deferred. Phase 4 is
in-progress, with no token-reduction result claimed yet.

At Phase 3 closure: validator passed for 9 skills and local links, 129 unit tests
passed, and the reproducible archive contained 106 files with a verified SHA-256
checksum.


## Phase 4 token optimization

Phase 4 added a selective context optimizer and a repeatable eight-case benchmark. The
baseline includes full memory, full tool output, and full source. The optimized context
selects only project-scoped relevant memory, filters noisy tool/source lines, keeps
required facts and failure/fix evidence, copies critical constraints verbatim, and
references complete raw evidence through `raw://` stores.

Measured with `tiktoken:o200k_base`:

| Metric | Result |
| --- | ---: |
| Median context reduction | 63.17% |
| Minimum reduction | 60.24% |
| Required facts retained | 8/8 |
| Critical constraints preserved | 8/8 |
| Raw tool evidence recoverable | 8/8 |
| Raw source evidence recoverable | 8/8 |
| Gate | pass |

This is a context-retention benchmark, not a live model-answer benchmark. It does not
claim identical answers from every model; it proves that the optimized context retains
every declared required fact and constraint and that raw evidence is not lost.

At Phase 4 closure: validator passed for 9 skills and local links, 139 unit tests
passed, and the reproducible archive contained 112 files with a verified SHA-256
checksum.


## Phase 5 UI/UX intelligence

Phase 5 added three distinct skills and a browser-backed fixture suite:

- `ui-design-intelligence`: direction, hierarchy, tokens, responsive rules, and
  enterprise profiles for tables, filters, approvals, long forms, reconciliation, and
  dense financial data.
- `ui-implementation`: implementation in the existing stack, responsive behavior,
  keyboard access, and empty/loading/error states.
- `ui-quality-verification`: visual, responsive, keyboard, accessibility, and state
  audits.
- `browser-diagnostics` now explicitly owns unexplained failure investigation and
  hands planned audits to `ui-quality-verification`.

Fixtures exist for plain web, React/Vite, and Next.js. Six screenshot baselines cover
360 and 1440 CSS pixels. The local browser runs exercised keyboard focus order, visible
focus, filter/selection/bulk approval, responsive reflow, empty/loading/error/retry,
and console errors.

| Check | Result |
| --- | ---: |
| Plain + React checks | 35/35 |
| Next checks | 12/12 |
| Screenshot baselines | 6 |
| Next production build | pass |

Screenshot comparison is tied to local Chrome and fonts. Automated checks do not replace
an assistive-technology review, and the fixtures do not test backend authorization.

At Phase 5 closure: validator passed for **12 skills** and local links, **145 unit
tests** passed, and the reproducible archive contained **149 files** with a verified
SHA-256 checksum.


## Phase 6 engineering intelligence and safety

Phase 6 adds four focused owners:

- `domain-modeling` clarifies terms, lifecycle states, events, and invariants.
- `spec-to-code-verification` traces testable requirements to implementation and test
  evidence.
- `skill-security-guard` reviews third-party skills before adoption and never installs
  them automatically.
- `transaction-safe-engineering` is optional and loaded only for money, ledger, batch,
  retry, reconciliation, or idempotency risk.

The deterministic safety suite passed eight positive/negative cases:

| Case | Result |
| --- | --- |
| Safe skill fixture | no findings |
| Unsafe skill fixture | rejected with 5 high-severity findings |
| Valid domain model | pass |
| Invalid domain model | rejected |
| Complete specification traceability | pass |
| Missing/orphan requirement references | rejected |
| Safe transaction cases | pass |
| Unsafe transaction cases | rejected |

The checks are fixture-level and heuristic. The security scanner is triage, not proof of
safety; domain and transaction checks validate declared controls, not production
behaviour.

At Phase 6 closure: validator passed for **16 skills** and local links, **152 unit
tests** passed, and the reproducible archive contained **178 files** with a verified
SHA-256 checksum.


## Phase 7 cross-agent packaging

Phase 7 adds a portable, host-neutral skill pack:

```sh
python scripts/package_skill_pack.py export --output dist/skill-pack.zip
python scripts/package_skill_pack.py verify dist/skill-pack.zip
python scripts/package_skill_pack.py import dist/skill-pack.zip --target /path/to/project
python scripts/package_skill_pack.py rollback --backup <backup> --target /path/to/project
```

The pack includes skills, UI metadata, the consuming snippet, adapter documentation,
license notices, `VERSION`, and a canonical manifest. Import is previewable, preserves
unrelated skills, and backs up every replaced path. Verification rejects duplicate
members, traversal paths, manifest mismatches, and tampered bytes.

Adapter compatibility checks cover Codex, Claude, and DSH uninstall and rollback entry
points. The portable layer does not import hooks, trust hooks, copy credentials, or
replace host-specific approval. The license inventory covers development/test
dependencies and records that they are not vendored.

Final current checks: validator passed for **16 skills** and local links, **161 unit
tests** passed, and the reproducible archive contains **183 files** with a verified
SHA-256 checksum. Phase 7 is complete; this is the final planned Version 2 phase.
