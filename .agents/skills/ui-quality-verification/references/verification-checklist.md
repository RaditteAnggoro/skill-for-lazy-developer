# UI quality verification checklist

## Evidence setup

- Record browser, version, route, viewport, role, and fixture data.
- Use isolated test data; do not copy session tokens into saved evidence.
- Capture a baseline screenshot before interaction.

## Visual and responsive

- Check 360, 768, and 1440 CSS-pixel widths.
- Check no unintended horizontal overflow.
- Check hierarchy, clipping, overlap, empty space, and touch targets.
- Check tables become usable cards/lists or a deliberate scroll region on narrow screens.
- Check totals, currency, decimals, and negative/credit states are aligned and legible.

## Keyboard and interaction

- Tab and Shift+Tab traverse all controls in a logical order.
- Focus is visible and not obscured by sticky elements.
- Enter/Space activate buttons, links, checkboxes, and custom widgets.
- Filters can be cleared without a pointer.
- Dialogs trap focus, close with Escape, and restore focus.
- Selection and bulk actions announce what will change.

## States

- Empty: explains why there is no data and what to do next.
- Loading: does not cause layout shift; prevents duplicate actions.
- Error: identifies the failed operation, preserves user input, and offers recovery.
- Success: confirms the affected record, not just “saved”.
- Disabled/permission-limited: explains why, rather than silently hiding the action.

## Enterprise checks

- Tables: stable identifiers, sort state, result count, active filters, selection.
- Approvals: requester, impact, risk, reason, confirmation, audit trail.
- Long forms: sections, inline validation, preserved values, sticky action.
- Reconciliation: matched/unmatched/ambiguous states, totals, exceptions.
- Financial data: tabular numerals, currency/period labels, no color-only meaning.

## Reporting

Report findings with route, viewport, reproduction step, expected/actual, and severity.
Separate unverified areas and automated limitations from observed evidence.
