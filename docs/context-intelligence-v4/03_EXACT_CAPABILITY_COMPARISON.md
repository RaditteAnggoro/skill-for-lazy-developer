# Capability comparison

| Capability | Representative upstream mechanism | Lazy Developer delivery | Evidence and disposition |
| --- | --- | --- | --- |
| Fast code lookup | ContextAtlas fallback, Serena symbols, ast-grep rules | Native file and symbol reads, plus explicit-scope token indexing and optional host capabilities | Native retrieval compared against lexical control. Semantic resolution remains a specialist capability |
| Incremental source state | Claude Context Merkle synchronization, Code-Index-MCP artifact freshness, Code Cortex index supervisor | Local SHA-256 check, single-file segment update, stale-anchor rejection, process restart | Tested edits and reopen. Full scope still read and hashed to detect changes |
| Structural and graph retrieval | CodeGraph index, Graphify extraction, tree-sitter parser | Python AST boundaries when available and bounded line windows otherwise; separate optional symbol provider | Verified excerpt and full-definition expansion. Graph extraction stays external |
| Semantic retrieval | sqlite-vec KNN, Claude Context embeddings, Cognee multi-retrieval | FTS5 and lexical fallback; current-source hydrator shared by both | Local top-1 benchmark covers explicit identifiers. Semantic retrieval decision deferred pending relevant misses |
| Source packing | Repomix security filter, Context Mode indexed output | Explicit file allowlist, scoped anchors, selective packet, raw evidence restore | Tested filtering, raw hash verification, and scope negatives |
| Session continuity | Engram compact search, Claude-Mem observation lifecycle, Graphiti episodes, Mem0 provider abstraction | Engram envelope and root-bound export, task ranking, expiry and optional source anchors | Live Codex lifecycle verified; DSH lifecycle fixture covers recall and scoped filtering |
| Compaction | tokf filters and RTK gain accounting | Opt-in conservative filtering known idle events, selected snippets, and exact guard preservation | Eight local fixtures and closed-book provider token measurement. Tool-enabled pilot failed the answer gate |
| Runtime tool discovery | MCP `tools/list`, cursor and list-changed notification | Host supplies transport and local allowlist. Discover selected shape, fall back under disconnect, and keep invocation separate | Protocol-tested against a synthetic stdio server. Host-native lazy inventory is host-specific |
| Evaluation | Agent Skill Eval, Skill Eval Harness, Skillbench, Promptfoo | Existing fixture workflow plus paired live runs, A/A, local exclusion of blocked telemetry and independent retrieval grading | Synthetic matched evidence on Codex. Broader host and upstream parity comparisons remain unmeasured |
| Telemetry | Langfuse format normalization | Provider counters, wall time and tools from Codex events, plus local estimates labeled separately | Observed counters and cache fields. No billing claims or external tracing dependency |

No new mandatory runtime or skill was added. [Repository and implementation sources](02_NEW_OPENSOURCE_RESEARCH.md), [local benchmark](05_RETRIEVAL_BENCHMARK.md), [live evidence](06_SKILL_AB_EVALUATION.md).
