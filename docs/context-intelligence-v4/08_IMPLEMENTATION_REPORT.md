# Context intelligence V4

V4 adds an optional source-packet builder, conservative context compaction, task-aware scoped memory, and capability-first MCP discovery to the existing 17 skills. A small task can still use a direct native read. Before acting on consequential findings, open the current complete source or original evidence.

```sh
python scripts/context_intelligence.py --workspace . --task 'find posting retry and ledger invariants' \
  --path scripts/check_transaction_safety.py --constraint 'Read-only review' --budget 1200
```

The default transient index requires no cache. Use `--profile balanced` for repeated lookups in the same root. Pass `--required PATH` when a complete file is mandatory. A response marked `needs_expansion` or `budget_exceeded` calls for a current source read or a narrower task with the same constraints.

| Component | Where it runs | Verification |
| --- | --- | --- |
| [Context index](../../scripts/context_intelligence.py) | Local Python, SQLite FTS5 with lexical fallback | Stale source, scope, incremental lookup, restart and full-source expansion |
| [Packet compaction](../../scripts/context_optimizer.py) | Opt-in offline capture comparison | Exact constraints, relevant facts and hash-checked original output |
| [Memory](../../integrations/codex/memory_runtime.py) | Existing optional Engram adapters | Codex recall, remember, handoff, fail-open, opt-out and uninstall canary. DSH focused recall through its lifecycle fixture |
| [MCP catalog](../../scripts/mcp_discovery.py) | Client-provided preconnected transport | Paginated discovery, authorization, unsupported schema and disconnect fallback |
| [Tool selection](../../.agents/skills/adaptive-workflow/references/tool-selection.md) | Existing workflow and host | Native fallback, relevant lazy discovery where supported and evidence checks before handoff |

The local packet saved 51.48% at median on eight fixtures. The calibrated long closed-book case used 52.15% less reported input at median and passed the structured gate in all three D trials. The short case saved 1.51%. The tool-enabled pilot failed its gate, so the package keeps direct native source reads and authorized tools for work that needs them. No host integration installs an MCP server or updates active skills automatically.

## Evidence index

- [01 Baseline audit](01_CURRENT_ARCHITECTURE_AUDIT.md)
- [02 Pinned upstream research](02_NEW_OPENSOURCE_RESEARCH.md)
- [03 Capability comparison](03_EXACT_CAPABILITY_COMPARISON.md)
- [04 Context architecture](04_PROPOSED_CONTEXT_ARCHITECTURE.md)
- [05 Retrieval benchmark](05_RETRIEVAL_BENCHMARK.md)
- [06 A/B/C/D evaluation](06_SKILL_AB_EVALUATION.md)
- [07 Resources and tokens](07_RESOURCE_AND_TOKEN_ANALYSIS.md)
- [09 Security and licenses](09_SECURITY_LICENSE_REVIEW.md)
- [10 Follow-up validation](10_ROADMAP_AND_REMAINING_GAPS.md)
