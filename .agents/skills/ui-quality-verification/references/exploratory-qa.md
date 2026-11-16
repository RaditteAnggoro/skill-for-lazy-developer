# Exploratory and adversarial UI QA

Combine planned audits with a small exploratory charter:

- choose a high-risk user goal and a bounded route;
- test empty, loading, error, permission, and success states;
- test keyboard-only traversal and focus restoration;
- test a narrow viewport and a long/dense dataset;
- look for duplicate controls, unnecessary confirmation, lost drafts, hidden selection,
  misleading labels, and excessive reloads;
- distinguish a real friction from a style preference; provide a counterexample;
- capture viewport, steps, expected/actual, and masked evidence.

Do not call a static screenshot a user journey. Do not claim accessibility compliance
from automated checks alone. If browser evidence is unavailable, label the check BLOCKED
and provide a manual reproduction checklist.
