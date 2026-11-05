---
name: domain-modeling
description: "Resolve ambiguous domain terms, states, events, and invariants before code or interface design depends on them. Use when language or lifecycle rules are inconsistent, not for routine implementation or unresolved product choices."
---

# Domain Modeling

Build a small, explicit model of the business domain so implementation and review use
the same words. This skill clarifies language and invariants; it does not decide product
scope or authorize a schema migration by itself.

## Establish the domain boundary

Identify the bounded context, the people or systems that own it, and the decisions that
depend on the model. Collect the terms actually used in source, tests, tickets, UI copy,
and operator runbooks. Treat disagreement as evidence to resolve, not as noise.

Route unresolved product choices to `feature-discovery`. Route a failure with an unknown
cause to `systematic-debugging`. This skill owns the model that those workflows consume.

## Build the model

Produce only the artifacts that answer the request:

- a glossary with one preferred term, aliases, and a concrete definition;
- the lifecycle states and allowed transitions;
- events that cause transitions, including rejection and compensation paths;
- invariants that must hold across every state;
- identifiers, units, currency, timezone, and ownership where relevant;
- open questions that materially change the model.

Use examples from real records. Distinguish an event that happened from a command that
requests it. Make invalid transitions explicit. Do not invent a universal model for
unrelated contexts; split them instead.

Read [modeling-worksheet.md](references/modeling-worksheet.md) for a compact template.

## Handoff and review

Store the model beside the code or documentation that owns it. Link terms to their
source evidence. Propose validation for machine-checkable invariants. Hand implementation
to `ui-implementation` or `lean-senior-engineering`; hand requirement-to-evidence checks
to `spec-to-code-verification`.
