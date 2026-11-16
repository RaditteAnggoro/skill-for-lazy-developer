# Exploratory browser charter

Use for a meaningful interactive change, not a trivial copy edit.

1. Inventory the journey: objective, route, environment, test user, synthetic data,
   expected business outcome, and prohibited side effects.
2. Choose a small charter around high-risk or recently changed components.
3. Exercise a happy path, a failure/empty path, a keyboard path, and a navigation or
   unsaved-state path where applicable.
4. Observe actual runtime with a browser. Use Chrome DevTools only for console/network/
   performance diagnosis; do not launch duplicate automation for the same evidence.
5. Record minimal steps, viewport, expected vs actual, console/network evidence, and
   masked screenshots.
6. Assess friction: redundant confirmation, duplicate controls, hidden selection,
   lost draft, focus handling, unnecessary reload. Challenge findings with a
   counterexample; do not report taste as a bug.
7. Fix only when implementation was requested, then rerun the failing journey and
   adjacent regression checks.

A screenshot alone is not a completed journey. Browser-unavailable checks are BLOCKED,
not passed.
