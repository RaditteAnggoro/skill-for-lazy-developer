# Enterprise data UX profiles

Use these as selective references. The task and data decide which profile applies.

## Dense tables

- Make the primary identifier the first stable column and keep row height predictable.
- Right-align numeric values and use tabular numerals; preserve separators and
  negative/credit meaning.
- Provide visible sort state, active filters, result count, and a clear empty result.
- Select rows with checkboxes and keep bulk actions visible only when selection exists.
- Use a responsive card/list alternative for narrow viewports, not horizontal scrolling
  as the only access path.
- Keep a row action reachable by keyboard and name the affected record in confirmation.

## Filters and search

- Show active filter chips with individual removal and a clear-all action.
- Distinguish “no records” from “no matches for these filters.”
- Preserve filters in the URL or saved view only when the task benefits from it.
- Announce result counts after changes; do not move focus unexpectedly.
- Provide a reset path that restores the unfiltered state.

## Approvals

- Show requester, amount/impact, age, risk, and current status before the action.
- Separate approve, reject, and request-changes actions; never use an ambiguous toggle.
- Require a reason for rejection or high-risk overrides.
- Keep the audit trail and confirmation visible and specific to the record.
- Prevent duplicate submission and show pending state until the result is known.

## Long forms

- Group fields into meaningful sections with a short progress/label.
- Validate at the field and at submission; preserve entered values after errors.
- Explain required fields before the user reaches the end.
- Support draft save only when persistence and privacy are defined.
- Keep the primary action sticky on long pages without covering content.

## Reconciliation

- Place source and target values side by side, with differences and totals aligned.
- Distinguish matched, unmatched, ambiguous, and manually resolved states.
- Use explicit match/unmatch actions and show the resulting totals immediately.
- Never auto-resolve a financial difference without an approval or documented rule.
- Provide an exception queue and a clear way back to the full record.

## Dense financial data

- Use tabular numerals, consistent decimal places, and right alignment.
- Label currency and period; do not rely on a symbol alone.
- Treat debit/credit, negative, and zero states explicitly.
- Use color as reinforcement, not the only signal.
- Keep totals, reconciliation status, and audit timestamps visible.
