# Phase 5 evidence — advanced engineering enhancements

## Implemented as existing-skill references

| Capability | Owner/reference | Evidence level |
| --- | --- | --- |
| API/GraphQL layer isolation | `systematic-debugging/references/api-debugging.md` | STATIC |
| Bounded spike | `research-plan-implement/references/spike-contract.md`, `feature-discovery/references/spikes-and-actions.md` | STATIC |
| Grounded citations/evidence ledger | `spec-to-code-verification/references/evidence-ledger.md` | STATIC |
| Document-to-action extraction | `feature-discovery/references/spikes-and-actions.md` | STATIC |
| AST structural search / dry-run | `architecture-map`, `adaptive-workflow/references/tool-selection.md` | STATIC |
| Bounded dynamic fan-out | `adaptive-workflow/references/delegation-policy.md` | SIMULATED |

`tests/hermes_enhancement_cases.yaml` contains twelve contract cases with positive and
negative controls. `tests/hermes_spec_matrix.yaml` accounts for all 48 specification
test IDs and labels evidence levels.

## Value and resource checks

- No new mandatory dependency, MCP, browser driver, index, or model provider was added.
- AST search is optional and requires an installed tool; native search is the fallback.
- Spikes are disposable and must have an explicit cleanup decision.
- Delegation remains 0 specialists for simple tasks, 1 when useful, at most 2 concurrent;
  no recursive fan-out.
- qmd/local indexing, darwinian scoring, and humanizer/style injection are deferred until
  a measured comparison justifies them.

## Limits

No live AST rewrite, browser journey, API request, or model comparison was run in this
phase. The evidence is static/simulated contract coverage, not proof of a performance
gain.
