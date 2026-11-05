---
name: ui-design-intelligence
description: "Define UI direction, hierarchy, design tokens, and enterprise data patterns before implementation. Use for design decisions, not for diagnosing a browser failure or implementing an agreed interface."
---

# UI Design Intelligence

Choose a visual and interaction direction that fits the product, its users, and the
existing design system. This skill produces design decisions and an implementation
handoff; it does not authorize a code change by itself.

## Establish the design context

Inspect the existing tokens, typography, spacing, color, components, density, and
responsive conventions. Identify the primary task, user role, frequency, data volume,
and consequence of error. Reuse the existing system before introducing a new one.

For an existing product, preserve its visual language unless the request explicitly
asks for a redesign. For a new interface, state the direction in a few concrete terms:
calm or dense, editorial or operational, high-trust or exploratory. Do not substitute
generic “modern” or “clean” labels for decisions.

## Define the system

Specify only the decisions needed for the interface:

- page hierarchy and primary action;
- layout, grid, spacing, and density;
- typography scale and numeric treatment;
- color roles, including semantic status that does not rely on color alone;
- component states: default, hover, focus, selected, disabled, loading, empty, error;
- responsive behavior and touch targets;
- content hierarchy for labels, help, and validation.

Use accessible contrast and a visible keyboard focus treatment. Prefer semantic HTML
and native controls over custom widgets. If a custom widget is necessary, define its
keyboard model and ARIA behavior before implementation.

## Enterprise data profiles

Read [enterprise-data-ux.md](references/enterprise-data-ux.md) when the interface
contains dense tables, filters, approvals, long forms, reconciliation, or financial
data. Apply only the profiles relevant to the task; do not turn every screen into a
dashboard.

## Handoff

Return a compact design brief, the affected components, responsive rules, state
requirements, and acceptance checks. Separate settled decisions from open choices
that materially change the result. Hand implementation to `ui-implementation`; pair
with `feature-discovery` only when product outcomes are unresolved.
