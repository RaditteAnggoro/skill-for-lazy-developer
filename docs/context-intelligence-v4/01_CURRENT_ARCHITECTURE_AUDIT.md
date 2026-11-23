# Baseline architecture

The baseline was pinned at `66b12c368364ee5ae78add552ad87ac349248a11` with the preceding local financial work included as the implementation baseline. Before the context changes, 17 skills validated and 300 Python tests passed. The eight existing context fixtures showed a 43.41% median reduction from raw capture to the previous packet, with packet sizes of 358–399 estimated tokens.

| Layer | Prior behavior | Gap measured or inspected |
| --- | --- | --- |
| Routing | The adaptive skill selects a small phase chain; [tool selection](../../.agents/skills/adaptive-workflow/references/tool-selection.md) prefers existing tools | Host tool catalogs differ; routing guidance alone cannot control the provider's prompt or dynamic inventory |
| Memory | [Codex runtime](../../integrations/codex/memory_runtime.py) validates project scope for Engram; optional DSH and Claude adapters | Scope prevents mix-ups, but relevance and current-source checks are separate problems |
| Source | Native search and optional symbol providers | No shared, bounded local source packet against explicit paths with a persistent revision check |
| Compaction | [Context optimizer](../../scripts/context_optimizer.py) summarizes fixture packets, records raw evidence and estimates tokens | Fixture estimates give no provider telemetry and can conceal workflow overhead |
| Evidence | [Phase receipts](../../docs/VALIDATION.md) track verified command outcomes; learning proposals require evidence | Static validation, deterministic retrieval, live agent output, and engine integration must stay independently auditable |

Trust flows from explicit task permission and normal project inputs to a fresh source read or an observed check. Historical memory and retrieved snippets can guide a read. They cannot grant permissions or prove completion.
