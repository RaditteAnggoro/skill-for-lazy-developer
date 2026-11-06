# Version 2 capability matrix

This matrix prevents capability growth from becoming skill sprawl. The detailed,
machine-checked ownership record is
[`tests/v2_phase_gate.yaml`](../tests/v2_phase_gate.yaml).

## Existing ownership

| User outcome | Owner | Boundary |
| --- | --- | --- |
| Select a workflow from a normal request | `adaptive-workflow` | Does not run every skill |
| Implement or review a clear change | `lean-senior-engineering` | Unknown failures route to debugging first |
| Diagnose an unexplained failure | `systematic-debugging` | A diagnosis-only request does not authorize a fix |
| Verify a change or claim | `verification-before-completion` | Not a ceremonial approval gate |
| Clarify consequential feature choices | `feature-discovery` | Clear small changes do not require an interview |
| Carry substantial work across modules or sessions | `research-plan-implement` | Not for small fixes |
| Explain architecture and impact | `architecture-map` | Explanation does not authorize refactoring |
| Assess a release candidate | `release-readiness` | Does not publish or deploy |
| Observe a browser-visible failure | `browser-diagnostics` | Static UI edits remain implementation work |

## Planned disposition

| Capability | Form | Reason |
| --- | --- | --- |
| Companion interaction | Lightweight core policy | Applies to every conversation and must remain small |
| Better requirement discovery | Extend `feature-discovery` | Existing ownership is already clear |
| Persistent memory and session continuity | Runtime service | Contract defined in Phase 2; storage, hooks, retrieval, and lifecycle integration remain Phase 3 |
| Context budget and tool-output filtering | Runtime service | Operates on retrieval and tool payloads, not user intent |
| Continuous learning | Verified memory pipeline | A lesson becomes durable only after evidence and consolidation |
| Agent-quality evaluation | Test harness | Measures behaviour; users should not invoke it as a workflow |
| Memory provider bake-off | Evaluation harness | Compares providers on one corpus; selection is not a user-facing workflow |
| Context optimization benchmark | Evaluation harness | Measures selective context and retention; not a user-facing workflow |
| UI design intelligence | Workflow skill | Defines UI direction and enterprise data behavior before implementation |
| UI implementation | Workflow skill | Implements agreed responsive interfaces and states |
| UI quality verification | Workflow skill | Audits visual, keyboard, responsive, and state quality |
| UI design intelligence | New focused skill | Owns design direction and design-system choices |
| UI implementation | New focused skill | Owns stack-aware implementation of an agreed design |
| UI quality verification | New focused skill | Owns visual, responsive, interaction, and accessibility audits |
| Enterprise data UX | Supporting reference | Routed only for dense data, approval, and reconciliation flows |
| Domain modeling | New focused skill | Owns terminology, states, events, and invariants |
| Specification-to-code verification | New focused skill | Owns deep requirement-to-evidence comparison |
| Skill security guard | New focused skill | Owns pre-adoption review of external skills |
| Transaction-safe engineering | Optional domain skill | Loaded only when money, ledger, batch, or idempotency risk exists |
| Phase 6 checker suite | Evaluation harness | Validates domain models, spec traceability, skill security, and transaction controls |
| Cross-agent support | Adapter layer | Each host has different permissions and lifecycle capabilities |
| Portable skill pack | Packaging layer | Host-neutral skills, snippet, docs, manifest, backup, import, and rollback |
| Phase orchestration | Skill behavior | Single-agent phase plan, re-routing, skill trace, and per-phase evidence |
| DSH adapter | Adapter layer | Skill discovery, routing, guarded MCP, and lifecycle hooks are implemented and live-verified |
| Codex lifecycle adapter | Runtime integration | `SessionStart` recall, explicit remember, opt-out, fail-open, verified handoff, and confirmed forget are implemented |
| Claude lifecycle adapter | Runtime integration | Settings merge, hook contract, controls, fail-open, and uninstall are tested; live verification is deferred |

## Phase 2 provider decision

Both candidate providers met the Phase 2 hard gates on the recorded corpus. **Engram
3.6.2 is the first provider for the Phase 3 runtime adapter** because it had lower
observed setup and query overhead and supports portable import. Ai-memory 3.4.0 stays
a supported alternate because its wiki, Git checkpoints, lifecycle hooks, and typed
handoff model are richer than this phase needed. The decision is specific to the
recorded trial and can be revisited after Phase 3 lifecycle tests. See the
[memory contract](V2_MEMORY_CONTRACT.md) and [evidence](V2_PHASE2_EVIDENCE.md).

## Overlap decisions

- **Feature discovery vs domain modeling:** discovery resolves product choices;
  modeling resolves terminology, states, events, and invariants.
- **Browser diagnostics vs UI quality:** diagnostics investigates an unexplained
  browser failure; UI quality performs a planned audit or post-change check.
- **Continuous learning vs evaluation:** learning writes verified reusable knowledge;
  evaluation measures behaviour and regressions without becoming memory.
- **Output filtering vs context budget:** filtering reduces one tool payload; the
  budget decides which information belongs in the task context.
- **Enterprise data UX vs UI design:** enterprise guidance stays a routed reference,
  not another always-visible skill description.

## New-skill rule

A capability becomes a new skill only when it has a distinct user intent, a reusable
multi-step workflow, an independently testable result, and no clean existing owner.
Otherwise it extends an existing skill, becomes a supporting reference, or belongs
in runtime and evaluation tooling.
