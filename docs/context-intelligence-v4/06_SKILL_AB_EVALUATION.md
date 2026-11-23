# Context A/B/C/D evaluation

A is the previous packet assembler. B selects relevant memory and explicitly supplied source snippets. C filters known idle events and deduplicates explicitly supplied snippets. D combines the two. E, an upstream live arm, was excluded because equivalent inputs, permissions, and host execution were unavailable. The long scenario appends 900 synthetic idle-heartbeat events. The short invoice fixture is a separate control. The grading oracle stays outside the model prompt.

```sh
python scripts/run_context_intelligence_benchmark.py --output .agents/artifacts/context-local.json
python scripts/run_context_intelligence_benchmark.py --live --model gpt-6.2-sol --effort low --trials 3 \
  --output .agents/artifacts/context-live.json
```

Use a fresh output path. The opt-in live runner uses disposable workspaces, a sanitized environment and a host isolation preflight. It records source, corpus and packet hashes, cache counters, tool calls, and timings. The closed-book profile disables shell access in every arm. The long case rotates submission order and runs paired arms concurrently, so timings include scheduling and provider variability. This is a context-packet comparison, not an installation-wide measure of skill quality.

| Fixture | A | B | C | D |
| --- | ---: | ---: | ---: | ---: |
| Invoice reconciliation | 379 | 274 | 252 | 186 |
| Payment retry | 381 | 279 | 263 | 197 |
| Refund approval | 373 | 268 | 246 | 180 |
| Ledger batch | 399 | 293 | 268 | 202 |
| Customer export | 358 | 258 | 236 | 170 |
| Inventory sync | 367 | 264 | 245 | 179 |
| Auth migration | 365 | 264 | 241 | 175 |
| Release rollback | 367 | 263 | 238 | 172 |

These are local `o200k_base` estimates. D retained the required facts, exact constraints, and verified raw recovery in 8/8 cases. Median paired reduction was 51.48%.

## Observed live results

Codex CLI 0.167.0 and `gpt-6.2-sol`, low effort, three rounds per arm. The calibrated gate checks that the response is nonempty, contains all required facts across answer and evidence, cites three exact observation lines, copies all constraints exactly, and makes zero tool calls. It does not assess nuanced prose equivalence or broader agent decisions.

| Case | Arm | Gate passed | Median input tokens | Median output tokens | Median wall seconds |
| --- | --- | ---: | ---: | ---: | ---: |
| Long ledger | A | 3/3 | 26,259 | 160 | 10.31 |
| Long ledger | B | 3/3 | 26,152 | 170 | 10.34 |
| Long ledger | C | 3/3 | 12,630 | 165 | 10.45 |
| Long ledger | D | 3/3 | 12,564 | 168 | 11.17 |
| Short invoice | A | 3/3 | 12,741 | 131 | 9.30 |
| Short invoice | D | 3/3 | 12,548 | 146 | 9.62 |

A/A passed 2/2 separately. Median paired D input reductions were **52.15%** long and **1.51%** short. Cache reads ranged from 0 to 10,624 input tokens per trial and cache writes reported 0. The paired reduction uses total reported input, including cached input.

The first tool-enabled pilot used a different response gate. A/A passed 1/2. Long-case results were A 2/3, B 0/3, C 1/3, D 1/3. Short results were A 3/3 and D 2/3. D invoked a tool in every long trial and saved 1.49% median reported input on that case. The pilot failed its gate, so retain the ordinary source and tool workflow for tasks requiring exploration. The calibrated closed-book run establishes only its narrower result.

Reproduction identifiers for the calibrated run:

- Baseline commit `66b12c368364ee5ae78add552ad87ac349248a11`
- Corpus SHA-256 `13d7281fb92f85622983065228ea544e96e473894dee31721b89f3a17a3cee7f`
- Runner SHA-256 `f5c167a87e9cf5c8aef345ab1afa12aa8f19a617928948acc6680723d39a61c7`
- Optimizer SHA-256 for the live run `d8dd0ce9cd111427be2b348c6181821facd05df82cfcc5faf2127b3732cad4d0`. A later regression fix prevents a rejected memory record from returning through a duplicate ID. All eight live packet hashes and eight local fixture metrics remained identical.

## Fifteen-scenario coverage ledger

| Scenario | Available check | Evidence level |
| --- | --- | --- |
| Small Java fix | Existing Java repayment fixture and financial static scanner | Fixture regression, no matched live context run |
| Large Spring Boot navigation | Source anchors and synthetic named Java fixture | Local check, no large-project live run |
| Spring Batch boundary | [Real framework/database tests](../enterprise-financial-engineering/FAILURE_INJECTION_RESULTS.md) | Engine integration |
| PostgreSQL query | Financial SQL anchors and real engine checks | Static plus engine integration |
| Duplicate repayment | Existing replay checks and enterprise batch fixture | Runtime fixture |
| Cross-module impact | Existing impact evaluation fixtures and symbol-index tests | Local regression |
| React UI/browser | Existing browser CI workflow | Browser integration outside context A/B |
| Session restart | Isolated Codex adapter with Engram | Live lifecycle |
| Stale memory | Both adapter fixtures with changed digest and expiry | Local regression |
| Repeated output | Long-ledger comparison | Live A/B/C/D plus pilot |
| MCP unavailable | Disconnected protocol fixture and native fallback | Local protocol test |
| Irrelevant/malicious content | Scoped index and memory rejection, MCP description ignored | Local negative controls |
| Overlapping projects | Index restart and root binding, adapter scoping | Local regression and isolated Codex lifecycle |
| Source changed after indexing | Paired stale rejection and refresh benchmark | Local timing and regression |
| Misleading initial snippet | Explicit expansion retrieves guard outside snippet | Local timing and regression |

These evidence levels are independent. Fifteen live provider comparisons and upstream parity were not established.
