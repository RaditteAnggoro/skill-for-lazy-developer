# Local source retrieval benchmark

Run `python scripts/run_context_retrieval_benchmark.py --trials 9`. Each trial writes six target documents and 60 distractors into a disposable workspace, performs seven rounds of six named lookups, expands each first hit to inspect its deliberately separated guard, edits one source, tests stale rejection and refresh, and reopens the persistent profile. Each query has one predetermined relevant document. Timing covers retrieval plus revision-checked excerpt and full-file reads. These synthetic symbol searches favor explicit names. Short, ambiguous prose, real large repositories, and cross-language semantic edges require separate fixtures.

| Profile | Engine | Top-1 hits | Guard expansions | Stale rejected / recovered | Cold build (median ms) | Lookup + hydration (median ms) | Single-file refresh (median ms) | Persistent bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Lexical control | Python term overlap | 378/378 | 378 | 9/9 | 62.19 | 0.6529 | 40.86 | 0 |
| LIGHT | In-memory SQLite FTS5 | 378/378 | 378 | 9/9 | 61.65 | 0.3238 | 38.37 | 0 |
| BALANCED | SQLite FTS5 | 378/378 | 378 | 9/9 | 62.74 | 0.3525 | 39.07 | 90,112 |

SQLite 3.54.0 on the local development Mac. BALANCED reopened in 0.46 ms median. Each profile indexed only one changed document per refresh while reading and hashing the selected paths to detect changes. With one relevant result per query and one selected hit, observed precision@1 and recall@1 were both 1.00. The timings measure this fixture and host only. ADVANCED and upstream engines were not run against this corpus.
