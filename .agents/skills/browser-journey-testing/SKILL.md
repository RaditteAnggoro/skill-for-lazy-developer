---
name: browser-journey-testing
description: "Exercise user journeys in a real browser and compare UI behavior and presentation with the agreed product and design expectations. Use for meaningful UI changes or requested end-to-end browser checks."
---

# Browser Journey Testing

Check the experience a user actually encounters. Respect the requested scope; this
workflow does not itself authorize a redesign or changes to production data.

## Prepare the journey

Identify the user goal, affected routes, roles, expected outcomes, design references,
existing component conventions, and relevant test data. Translate these into a short
journey and observable acceptance checks. For materially different design directions,
resolve the product decision with the user; otherwise choose a reasonable default.
Inspect available browser tools, project scripts, and test configuration. Use an
available browser connection or existing automation; Playwright or an MCP server are
options, not assumed capabilities. Inspect start commands before running them. Use a
development or authorized test environment and isolated data. Do not send messages,
change real records, or perform financial actions without relevant authorization.

## Exercise and compare

Run the primary journey from entry through the visible result, not just a screenshot.
For affected paths, cover navigation, input, validation, submit, refresh/back, and relevant
loading, empty, error, permission, and success states. Check desktop and narrow viewports,
keyboard focus and operation, console errors and failed required requests. Choose cases
proportional to the change; test slow network, long content, and empty data when relevant.
Use explicit state waits. Compare actual behavior and presentation with the agreed brief,
reference, and existing design system. Check for repeated controls, duplicated messages,
unnecessary cards or copy, weak hierarchy, and generic decoration that obscures the task;
judge in product context rather than treating a particular style as inherently wrong.
Capture viewport, route, setup, observations, and useful screenshots or traces without
secrets. Add focused regression coverage when valuable and use the project framework.

For an unexplained failure, use `browser-diagnostics` to investigate. For a broader
visual, responsive, keyboard, and accessibility audit use `ui-quality-verification`.
Fix findings only when implementation is authorized, then rerun affected journeys.

## Report honestly

List journeys and states exercised, expected and actual outcomes, evidence, unresolved
issues and checks not performed. A build or static inspection is not a browser test. If
no browser is available, try the project's configured automation where feasible, report
browser verification as blocked, and provide a concrete manual reproduction checklist.
Do not claim that screenshots alone establish usability or accessibility compliance.
