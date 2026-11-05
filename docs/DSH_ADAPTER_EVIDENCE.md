# DSH adapter evidence

Date: **2026-11-05** (Asia/Jakarta)

Status: **DSH skill/memory adapter and lifecycle hooks standard-verified.** Live DSH
model delivery now passes after fixing message identity and moving recall to the
pre-step. Phase 3 is complete with `verified-with-deferred-claude`; Claude live
verification is deferred.

## Environment

- DeepSeek Harness `0.2.1-rc.5`.
- Model profile: `dsh-eval`, provider `deepseek-account`, model `deepseek-flash`.
- macOS 27.2 on arm64.
- Node `v24.22.1`.
- Engram `3.6.2` (official release, checksum verified).
- Python `3.9.6`.
- Disposable DSH profile, HOME, project, session, and Engram data directories.
- No production memory store and no cloud provider configured.

The DSH profile is local test configuration. It is not distributed because it may point
at local credentials; the repository only ships the adapter and bundle files.

## Standard verification

The target was the full standard in [ADAPTERS.md](ADAPTERS.md), not a three-prompt
smoke test.

| Area | Result |
| --- | --- |
| Skill discovery | 16 workflows detected in the live DSH catalog and by the adapter tests |
| Instruction installer | Create, check, idempotent install, uninstall, rollback, and user-content preservation pass |
| DSH routing corpus | 24 / 24 passed |
| Read-only boundaries | Included in routing cases |
| Interaction boundaries | Included in routing cases |
| Memory save/search/context | Pass on real Engram MCP server |
| Memory restart | Pass after stopping and restarting the MCP server |
| Memory delete | Pass; observation no longer searchable |
| Cross-project isolation | Pass in both directions (`alpha` ↔ `beta`) |
| Privacy guard | Pass (unit + bundle row): direct Engram accepted the canary; `inspectWrite` rejects it; DSH itself also refused the end-to-end write, so the Host denial path was not observed live |
| Provider failure | Pass: with Engram absent, DSH still answered ordinary work and exited 0 |
| Bundle install | Pass in a disposable DSH profile |
| Bundle uninstall | Pass: MCP and guard rows removed and DSH still worked |

### Routing delta and calibration

The first full DSH run passed 17 of 24 cases. The failures were host-specific routing
differences, not skill-loading failures:

- browser failure primary/support order was inverted;
- browser performance and documentation edits gained unnecessary support skills;
- one read-only route returned `user_message: null`;
- the router appeared as a supporting skill;
- an explicitly constrained planning request became a question;
- release assessment gained unnecessary verification support;
- a verification-only request gained debugging support;
- a casual Indonesian route used formal “Saya akan” language;
- a substantial migration added `lean-senior-engineering` even though
  `research-plan-implement` already owned implementation.

The DSH overlay in [`adapters/dsh/AGENTS.dsh.md`](../adapters/dsh/AGENTS.dsh.md) now
states the missing host-specific boundaries. Targeted reruns passed those cases, and
the final full-corpus run passed **24 / 24**. The runner also hashes the disposable
workspace before and after each case; a changed file fails the read-only check.

### Live skill catalog

The DSH profile reported exactly these nine names:

```json
["adaptive-workflow","architecture-map","browser-diagnostics","feature-discovery","lean-senior-engineering","release-readiness","research-plan-implement","systematic-debugging","verification-before-completion"]
```

The names also match the nine installed `SKILL.md` directories.

### Lifecycle increment

The Host plugin now registers DSH lifecycle behavior:

- `agent/created` prepares bounded Engram context;
- `agent/pre-step` injects recall with the actual user prompt and handles explicit
  remember/show/opt-out/two-step-forget prompts;
- `agent/turn-stopping` writes a bounded handoff, verified only with linked
  verification evidence.

The Node lifecycle test passed recall, remember, show, opt-out, handoff, and
sensitive-write skipping against a fake Engram process. The first live runs failed
with `TRANSPORT: DeepSeek Messages transport failed`. The cause was not account
authentication: the plugin injected a user-context message without a complete DSH
message identity (`id`), and injecting it at `agent/created` produced a context-only
turn before the real prompt. The fixed plugin adds an identified message during
`agent/pre-step`, gated on an actual user prompt.

After the fix, a live disposable DSH run passed:

- recall of `DSH-FINAL-7319`;
- explicit remember stored as a verified user note;
- bounded handoff stored on `agent/turn-stopping`;
- project opt-out blocked subsequent recall and memory tools;
- two-step forget kept the memory after the first prompt, deleted it only after
  confirmation, and cleared the pending state;
- missing Engram still answered ordinary work (`OK`);
- bundle uninstall removed both rows and DSH still answered.


### Memory and privacy detail

The direct Engram MCP server **accepted** the synthetic canary
`sk-test-CANARY-...`; provider-native privacy is therefore not sufficient for this
adapter. The Host guard in
[`integrations/dsh/companion-memory/index.js`](../integrations/dsh/companion-memory/index.js)
rejects the canary and also blocks obvious GitHub/AWS credentials, private keys,
bearer tokens, secret assignments, email addresses, content over 4,000 characters, and
raw prompt capture. The live DSH model refused to issue the canary write on policy
grounds before the guard was exercised, so the end-to-end denial is a unit/bundle
check, not an observed live denial.

The verifier also deletes the canary it used for the provider observation. This is a
test fixture, not a production credential. The standard result proves the guard logic
and bundle composition, not a live tool denial.

## Commands

```sh
python scripts/dsh_adapter.py check --root <consumer-project>
python scripts/dsh_adapter.py install --root <consumer-project>
python scripts/dsh_adapter.py uninstall --root <consumer-project>
python scripts/dsh_adapter.py rollback --root <consumer-project> --backup <backup>

python scripts/run_dsh_routing_evals.py \
  --profile <dsh-profile> \
  --artifacts .agents/artifacts/dsh-routing

python scripts/verify_dsh_memory_bundle.py \
  --engram-bin /path/to/engram \
  --node /path/to/node

python scripts/verify_dsh_bundle_lifecycle.py \
  --dsh /path/to/dsh \
  --dsh-home /path/to/dsh-home \
  --source-profile <profile-with-credentials>
```

## Maintenance checks

The current repository checks validate sixteen skills and local links, pass 145 unit
tests, and build a reproducible 91-file archive with a verified SHA-256 checksum. The
DSH profile, model credentials, Engram data, and provider binaries remain local test
artifacts and are not distributed.

## Limits

- One DSH profile, one model, and one repetition. Re-run after model, profile,
  instruction, or skill changes.
- The routing overlay is DSH-specific; it does not change the Codex corpus or claim
  identical behaviour on Claude.
- The Host guard is pattern-based. It cannot replace a data-loss-prevention system,
  provider retention review, or user review of what is saved.
- Automatic recall and handoff are implemented by the lifecycle plugin; verified
  handoff depends on the transcript evidence checks described above.
- The DSH adapter does not install itself. Bundle installation executes Host code and
  requires explicit approval.
- Claude live verification remains deferred; the Codex runtime has separate evidence.
