# Hermes-inspired enhancements

This document adapts **ideas and methods**, not Hermes executable code or upstream
prompts. Hermes is not a runtime dependency, and no affiliation or endorsement is
claimed. See [SOURCES.md](SOURCES.md) for references and terms.

| Hermes idea | Existing owner | Implemented change | Evidence level |
| --- | --- | --- | --- |
| `dogfood` / exploratory QA | `browser-journey-testing`, `ui-quality-verification` | Bounded journey charter and exploratory QA reference | Static contract |
| Adversarial UX | `ui-design-intelligence`, `ui-quality-verification` | Counterexample-based friction review | Static contract |
| `requesting-code-review` | `lean-senior-engineering`, `verification-before-completion` | Review/simplification and pre-commit evidence gate | Static contract |
| `test-driven-development` | `lean-senior-engineering`, `systematic-debugging`, `transaction-safe-engineering` | Risk-weighted invariant-first guidance | Static contract |
| `skill_manage` / `/learn` | `adaptive-workflow`, `skill-security-guard` | Local proposal, scan, dedupe, evaluation, human review | Repository integration |
| `simplify-code` | `lean-senior-engineering` | Diff-focused simplification without weakening invariants | Static contract |
| `spike` | `feature-discovery`, `research-plan-implement` | Disposable spike contract | Static contract |
| `ast-grep` | `architecture-map`, `lean-senior-engineering`, `tool-selection` | Optional structural search with dry-run | Static contract |
| `rest-graphql-debug` | `systematic-debugging` | Layered HTTP/GraphQL diagnosis reference | Static contract |
| `grounded-citations` | `spec-to-code-verification`, `architecture-map` | Evidence ledger and source anchors | Static contract |
| `document-to-action-items` | `feature-discovery`, `spec-to-code-verification` | Provenance-preserving action extraction | Static contract |
| `dynamic-workflow` | `adaptive-workflow` phase orchestration | Bounded delegation node; no second router | Simulated policy |
| `qmd` / local index | Existing memory/docs | Deferred until measured against existing retrieval | Not implemented |
| `darwinian-evolver` / scoring | Existing benchmark infrastructure | Deferred; no automatic promotion | Not implemented |
| `humanizer` / popular designs | UI/docs references | Deferred; no default style injection | Not implemented |
| Hermes product/social/marketing skills | None | Excluded from core engineering scope | Not implemented |

The repository does not install or require Hermes, a new MCP, a browser driver, a model
provider, or a database. Optional tools stay optional and capability-gated.
