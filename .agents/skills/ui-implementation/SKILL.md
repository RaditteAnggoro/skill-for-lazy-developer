---
name: ui-implementation
description: "Implement an agreed UI design in the project's existing stack, including responsive behavior, keyboard access, and empty/loading/error states. Use when the intended interface is already clear; do not invent a new design direction."
---

# UI Implementation

Turn an agreed design into working interface code using the project's existing
components, tokens, and conventions. If the design direction is unresolved, route to
`ui-design-intelligence`; if the interface is visibly broken and the cause is unknown,
route to `browser-diagnostics`.

## Inspect the implementation context

Read the affected components, styles, data flow, tests, and build commands. Identify
the design tokens and primitives already in use. Reuse them before adding a wrapper or
dependency. Check the API states the UI must render: loading, empty, partial, error,
success, disabled, and permission-limited.

Preserve explicit user and design decisions. Do not silently redesign spacing, copy,
navigation, or interaction patterns while implementing a local change.

## Build the interface

- Use semantic HTML and native controls where possible.
- Implement keyboard order, visible focus, labels, names, and error associations.
- Make responsive behavior intentional: test narrow and wide viewports, not only the
  desktop screenshot.
- Implement empty, loading, and error states as first-class states, not afterthoughts.
- Keep destructive or financial actions explicit, reversible where possible, and
  clear about the affected record.
- Avoid layout shift, horizontal overflow, and color-only status signals.

For enterprise tables, filters, approvals, long forms, reconciliation, and dense
financial data, follow the selected profile in
[`ui-design-intelligence/references/enterprise-data-ux.md`](../ui-design-intelligence/references/enterprise-data-ux.md).

## Verify while building

Use the project's existing test setup. Add focused interaction tests for meaningful
behavior, not snapshots of every static element. Check at minimum:

- keyboard traversal and focus visibility;
- narrow and wide viewport behavior;
- empty, loading, and error states;
- the primary success path;
- no console errors or failed required requests.

Hand the result to `ui-quality-verification` when a visual/interaction audit is
requested or when the change affects a critical enterprise workflow.
