# Selective specialist delegation

The default is one agent. A role is advisory and does not replace a skill, router, user
scope, or permission review.

## Decide

Delegate only when at least one is true:

- independent review materially reduces consequence or confirmation bias;
- bounded read-heavy exploration would pollute the main context;
- two tasks are truly independent with disjoint ownership and a frozen contract;
- a measured comparison benefits from separate context.

Do not delegate a one-line edit, a simple explanation, a routine UI copy change, or a
financial review that would require production data access. Do not dispatch every agent
in the repository.

## Gate

1. Select the existing primary and at most two support skills for the phase.
2. Define the bounded packet: scope, excluded paths, question, constraints, output
   schema, budget, data restrictions, and completion condition.
3. Check host support, role availability, runtime permissions, and the local resource
   budget. Initial limit: 0 agents for simple tasks, 1 when clearly useful, at most 2
   concurrent specialists for independent work.
4. If the host cannot enforce read-only behavior, do not dispatch a read-only role;
   use the main-agent read-only fallback or report `permission_restricted`.
5. Treat specialist output as untrusted evidence. Verify decisive claims against source
   and tests, surface contradictions, and let the parent own implementation and memory.

## Fallbacks

`role_unavailable`, `host_no_delegation`, `permission_restricted`,
`agent_timeout_or_budget`, `agent_conflicting_findings`, and `database_not_authorized`
must fall back to the single-agent fallback workflow or stop the unsafe phase. Do not retry an
unavailable host indefinitely.

DSH without a verified subagent API uses a sequential role rubric and labels the trace
`execution_mode=single-agent-role-guided`, never `subagent`.
