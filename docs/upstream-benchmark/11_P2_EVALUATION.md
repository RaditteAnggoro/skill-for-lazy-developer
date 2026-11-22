# 11 — P2 role dispatch and source navigation

## Host dispatch

| Host | Evidence | Result |
| --- | --- | --- |
| Codex CLI 0.167.0 with GPT-6.2 Sol | A local app-server reported one child start and completion. The child returned the role-only fixture marker and identified `sample.py:4` calling `bridge.py:1`. The parent relayed the same anchors. The workspace digest stayed unchanged. | **HOST_INTEGRATION** for `ld-codebase-explorer` on the synthetic fixture. |
| Claude Code 2.1.322 | Project wrappers render consistently. The installed CLI reported `loggedIn: false`. | **AUTH_REQUIRED** for live dispatch. |
| DSH | The adapter has no verified dispatch API. Its deterministic evaluator exercises the sequential role-guided fallback. | **UNSUPPORTED** for live dispatch in this adapter. |

Earlier non-interactive probes returned no qualifying child event. The app-server
diagnostics showed that ephemeral sessions did not have a parent rollout to restore
during spawn. The [canary](../../scripts/verify_role_dispatch.py) uses a temporary
Codex home and lets the host write the rollout there. It checks a read-only sandbox,
denies a synthetic filesystem write, disables network access for tools and uses no
repository or production data. Child events must match source anchors and a random
role marker. The printed summary retains only observations and status. See the
[Codex subagent permission model](https://learn.chatgpt.com/docs/agent-configuration/subagents).

```sh
python scripts/verify_role_dispatch.py --model gpt-6.2-sol
```

The `--timeout` budget is independent of model output. A short-budget run returned
`agent_timeout_or_budget` with `single-agent-role-guided` and an unchanged fixture.
Exit 3 means that this invocation did not verify dispatch. A successful canary
applies to the exact profile exercised. Consumer sessions still check host permissions
and fall back when they cannot confirm a child result.

## Structural navigation experiment

The [benchmark](../../scripts/run_symbol_index_benchmark.py) compares direct ripgrep
searches for an unaliased call name with a Python AST index rebuilt from the same
[two-file fixture](../../tests/enhancement/fixtures/symbol_index/). Ground truth
includes a direct call, an imported alias and an imported module qualifier. The
fixture also contains shadowed names, a comment and dynamic dispatch. Results were
stable across nine alternating measurements per arm.

| Method | Correct anchors | Missed | Extra candidates | Returned bytes |
| --- | ---: | ---: | ---: | ---: |
| Lexical ripgrep searches | 2 | 1 | 3 | 336 |
| Import-aware AST prototype | 3 | 0 | 0 | 124 |

```sh
python scripts/run_symbol_index_benchmark.py --repeats 9
```

The script reports median wall time for each arm, including ripgrep process startup.
This tiny fixture measures exact callsite extraction, and the bytes are emitted source
hints rather than token or memory measurements. A reviewer can still use lexical
search with import context. The prototype handles unique top-level functions and
imports in flat Python source. Runtime dispatch, wildcard imports, rebinding and
unsupported scope patterns need source review. No upstream runtime or code was
imported. Keep native search as the default and use structural evidence when aliases
or shadowing obscure the path. The experiment adds no consumer dependency or index
state. Rollback consists of removing the optional script and its fixture.
