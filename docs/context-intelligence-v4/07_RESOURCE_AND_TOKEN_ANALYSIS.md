# Resource and token analysis

| Workload | Preferred approach | Observed cost or consideration |
| --- | --- | --- |
| Small task or known definition | Direct native read | Skips setup and ranking. Short Codex control saved a median 1.51% of reported input |
| Repeated cross-file source lookup | BALANCED local index after initial scope is known | 90,112 bytes for 66 synthetic files. Cache reopen took 0.46 ms median |
| Large, repetitive captured logs with known evidence | Opt-in compaction and raw recovery | 51.48% estimated packet savings across eight fixtures. The long closed-book Codex case saved 52.15% median reported input |
| Long tasks that require tool follow-up | Measure the entire interaction | The tool-enabled pilot saved 1.49% on the long case and failed its answer gate |
| Semantic or temporal graph workloads | Benchmark on a scoped, disposable project before adoption | Startup, schema, embeddings, graph maintenance, and new services add cost and trust boundaries. No comparable resource evidence is available for this profile |

Local token estimates describe the text payload. Host-reported cumulative input includes repeated turns and prompt overhead. Cache reads and writes were reported separately in the closed-book comparison, and response tokens and wall time were captured by the runner. Reported counts establish neither billed subscription consumption nor invoice amounts. The runner does not observe effective context-window occupancy, compute utilization, or monetary cost. Indexing and compaction call no model. Process RSS and CPU were not isolated by profile.
