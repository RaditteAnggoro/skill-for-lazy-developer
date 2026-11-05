# Version 2 Phase 2 evidence

Date: **2026-11-05** (Asia/Jakarta)

Status: **Phase 2 complete**. At the Phase 2 gate, Phase 3 remained blocked until its
own setup, hook, failure, and handoff checks passed. Phase 3 has since started with a
Codex-first vertical slice. The contract is in
[`docs/V2_MEMORY_CONTRACT.md`](V2_MEMORY_CONTRACT.md).

## Scope of the trial

The trial compared two candidate providers behind the same provider-neutral adapter
and corpus:

- **ai-memory 3.4.0** ([release](https://github.com/akitaonrails/ai-memory/releases/tag/v3.4.0)), `ai-memory-macos-aarch64.tar.gz`.
- **Engram 3.6.2** ([release](https://github.com/Gentleman-Programming/engram/releases/tag/v3.6.2)), `engram_3.6.2_darwin_arm64.tar.gz`.

Both binaries came from their official GitHub releases. Their published SHA-256
checksums were verified before execution:

- ai-memory: `67399327a7b553ca4044efae65526ef8b42aca429ec6c8121714c536021b0911`.
- Engram: `3d351cc01f17d90c81466483b4d97ddda7a59d9be29a0a2c3aabcdc6861f36e7`.

They were unpacked under the ignored `.agents/artifacts/` directory and were not
committed or distributed with this repository.

The test used:

- macOS 27.2 on arm64;
- Python 3.9.6;
- disposable home, project, data, and artifact directories for each provider;
- loopback-only local services;
- no LLM, embedding, cloud, or remote synchronization configuration;
- the nine-record / twelve-query corpus in
  [`tests/memory_bakeoff_cases.yaml`](../tests/memory_bakeoff_cases.yaml);
- one full run per provider and one combined final run.

The providers were exercised through their local CLI and HTTP surfaces. The adapter
performed the contract checks: it wrote the neutral envelope, filtered stale,
superseded, untrusted, low-confidence, and wrong-project records, and rejected the
synthetic sensitive probe before storage.

## Results

| Check | ai-memory 3.4.0 | Engram 3.6.2 |
| --- | --- | --- |
| Recall | 12 / 12 | 12 / 12 |
| Stale leaks after contract filtering | 0 | 0 |
| Cross-project leaks | 0 | 0 |
| Synthetic secret rejected before storage | yes | yes |
| Canary found in store or export | no | no |
| Delete then restore | pass | pass |
| Restart then recall | pass | pass |
| Portable import | no | yes |
| Export format | OKF 0.2 tarball | JSON 0.2 |
| Export size | 1,345 bytes | 7,208 bytes |
| Setup time (observed, one run) | 485.4 ms | 231.3 ms |
| Median query time (observed, one run) | 591.8 ms | 2.8 ms |
| Median returned context | 52 chars | 52 chars |
| Store size | 1,285,062 bytes | 2,502,241 bytes |
| Hard gate | pass | pass |

The recall corpus includes direct token queries, natural-language queries,
superseded and stale decisions, an untrusted prompt-injection record, a cross-project
isolation probe in both directions, and a no-result query. Natural queries are
expanded to an `OR` expression for FTS and Engram is asked for `match_mode=any`, so
the same user-style query is not reduced to an all-terms-required lookup.

Query time includes adapter process and HTTP overhead, not just the provider's
database work. It is useful for relative operational comparison in this harness, not
as a universal latency benchmark.

## Decision

**Engram is the first provider for the Phase 3 runtime adapter.** Both candidates met
the Phase 2 hard gates. Engram had lower observed setup and query overhead and
supports both export and import in the tested path. Ai-memory remains a supported
alternate for a later adapter because its wiki, Git checkpoints, lifecycle hooks, and
typed handoff model are richer than this phase needed.

This recommendation is not a claim that Engram is universally better. Phase 3 must
still test the actual Codex lifecycle, automatic recall, verified handoff, fail-open
behaviour, and user controls. If those trials expose a gap, the provider decision can
be revisited without changing the contract.

The machine-readable summary is
[`tests/memory_bakeoff_evidence.yaml`](../tests/memory_bakeoff_evidence.yaml).

## Limits

- The corpus is synthetic and small. One repetition per provider does not establish
  statistical significance or broad retrieval quality.
- Status and trust filtering is **adapter-enforced** because neither provider natively
  owns this contract. The trial measures the adapter-plus-provider pair.
- The privacy canary was rejected before the provider was called. This proves the
  adapter boundary, not the upstream provider's own secret scrubbing.
- Raw conversation capture, lifecycle hooks, Codex integration, concurrent writers,
  crash recovery, network loss, and fail-open behaviour were not tested in Phase 2.
- Ai-memory's test path used FTS without the optional embedding model; Engram used its
  local SQLite/FTS path. The trial does not compare hosted or vector retrieval.
- The test used loopback services with disposable directories. It does not certify a
  shared, remote, or multi-user deployment.
- Provider versions and behavior change. Re-run the corpus before adopting a newer
  release; do not copy these numbers to a different version.

## Reproduction

Download the official release artifacts and verify their published checksums. Then:

```sh
python scripts/validate_skills.py
python -m unittest discover -s tests -v
python scripts/run_memory_bakeoff.py \
  --ai-memory-bin /path/to/ai-memory \
  --engram-bin /path/to/engram \
  --artifacts .agents/artifacts/phase2/reproduction
```

The runner fails closed when a binary is missing. It does not download, install,
register hooks, or modify the user's normal provider configuration. Inspect the
provider's license and privacy model before running it against non-disposable data.
