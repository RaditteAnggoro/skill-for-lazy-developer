# Matched skill benchmark

All four arms reviewed the same three synthetic source files with GPT-6.2 Sol at
low effort through the same read-only Codex CLI profile. Ground truth was kept
outside the fixture. Three rounds rotated arm order. The grader checked exact
source lines for floating-point amount construction, read-before-write, swallowed
writer exception and a missing ownership fence. A safe decimal-string control
was visible to all arms.

| Arm | Graded rounds | Correct anchors | Extra anchors | Misses | Supplied context tokens | Host input tokens, total | Host output tokens, total | Tool calls | Wall seconds, total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A. Baseline transaction skill | 3/3 | 12/12 | 1 | 0 | 719 | 129,761 | 1,769 | 17 | 69.988 |
| B. Enhanced references | 3/3 | 12/12 | 0 | 0 | 3,199 | 149,540 | 1,759 | 10 | 65.265 |
| C. References and Java/SQL analyzer | 3/3 | 12/12 | 0 | 0 | 3,504 | 151,896 | 1,556 | 13 | 62.893 |
| D. Analyzer and selected references | 3/3 | 12/12 | 0 | 0 | 2,952 | 146,809 | 1,603 | 12 | 64.382 |

Anchor precision was 12/13 for A and 12/12 for B, C and D. Exact-anchor recall was
12/12 throughout. A cited the writer call one time as an extra anchor. In the
proposed fixes, the grader required an anchored regression-test description.
Each arm provided 12 such descriptions. The benchmark did not apply patches or
evaluate whether those tests would catch all defects. The separate PostgreSQL and
Spring Batch controls execute financial outcomes.

D reduced supplied guidance by 552 tokens relative to C on this fixture while
preserving identical detected anchors. The measured input totals include host
instruction and tool context. The results support a local context-size observation
and one extra anchor in A. The timing and tool counts do not establish speed or
accuracy on other tasks. Broader repairs, independent assessment of proposed tests,
and database performance comparisons require additional fixtures.

Reproduce with the [benchmark runner](../../scripts/run_financial_skill_benchmark.py).
Use a new ignored output path. The report fingerprints the engine inputs, fixture,
prompt and all four supplied contexts. Raw model text stays outside the retained report.

A separate four-arm smoke run following a reference clarification produced the
same four correct anchors in each arm. B cited the same extra writer-call anchor
seen in A in the first run. This supports treating the observed difference in
precision as a fixture observation, with no ranking between the arms.

## Executed repair comparison

The same model and effort repaired one SQLite repayment fixture in two matched
rounds with four isolated arms per round. The Java/SQL analyzer's repair-mode
hints refer to SQL extracted from that SQLite fixture. The independent visible
and hidden verifiers ran after the proposal in fresh sandboxes and never exposed
the holdout to the model. The holdout synchronizes competing writers, forces a
second-write failure, and checks exactly two durable balanced lines after retry,
reopen, and a different payload under the same key.

| Arm | Both visible and holdout passed | Blocked | Supplied context tokens |
| --- | ---: | ---: | ---: |
| A | 2/2 | 0 | 712 |
| B | 2/2 | 0 | 3,200 |
| C | 2/2 | 0 | 3,289 |
| D | 2/2 | 0 | 2,895 |

This comparison demonstrates equal fixture acceptance. Concurrent runs share the
machine and provider, so their elapsed times do not establish a latency ranking.
Novel or independently authored regression tests and model-generated changes to a
real Spring Batch project remain separate evaluation cases.

```sh
python scripts/run_financial_skill_benchmark.py --model gpt-6.2-sol --effort low \
  --output .agents/artifacts/enterprise-review.json
python scripts/run_financial_skill_benchmark.py --mode repair --model gpt-6.2-sol --effort low \
  --trials 2 --concurrent-arms 4 --timeout 120 --output .agents/artifacts/enterprise-repair.json
```
