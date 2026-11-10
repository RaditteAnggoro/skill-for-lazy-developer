---
name: ui-quality-verification
description: "Audit a UI for visual, responsive, keyboard, accessibility, and state quality using browser evidence. Use for planned audits or post-change checks, not for diagnosing an unexplained browser failure."
---

# UI Quality Verification

Verify the interface as a user experiences it, not merely as a successful build. Use a
development or authorized test environment with representative data.

## Establish the audit surface

Confirm the URL, routes, viewports, user role, data setup, and whether the request is a
planned audit or a post-change check. Capture the current state before judging it.
For an unexplained failure, use `browser-diagnostics`; do not turn failure investigation
into a broad design audit.

## Check the interface

Use browser evidence and the project's existing automation where available:

- **Visual:** compare screenshots at representative desktop, tablet, and mobile widths;
  inspect hierarchy, spacing, clipping, overlap, contrast, and focus treatment.
- **Responsive:** verify reflow, touch target size, readable tables/cards, and absence of
  unintended horizontal overflow.
- **Keyboard:** traverse interactive elements with Tab/Shift+Tab, activate controls with
  Enter/Space, verify visible focus and a logical order, and check dialogs/filters.
- **States:** exercise empty, loading, error, success, disabled, and permission-limited
  states. Confirm messages identify the next action.
- **Accessibility:** check names, roles, labels, error associations, status announcements,
  and color-independent meaning.
- **Data journeys:** for approvals, reconciliation, and financial data, verify totals,
  selected records, confirmation, and audit evidence.

Compare the rendered result with the agreed design and product conventions; inspect
redundant actions, duplicate content, generic decoration, and hierarchy in context.
Use `browser-journey-testing` for end-to-end user journeys.

For enterprise profiles, use the selected checks in
[`references/verification-checklist.md`](references/verification-checklist.md).

## Record evidence and limits

Save screenshots and a concise findings list. Report the viewport, browser, route, data
fixture, and checks actually run. Distinguish visual/interaction evidence from backend
correctness. Do not claim accessibility compliance from a few automated checks.

If implementation is requested, make the smallest fix and rerun the affected visual,
keyboard, responsive, and state checks. A successful build alone is not completion.
