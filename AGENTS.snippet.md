## Development skills

Repository skills are in `.agents/skills/`. Users can describe a task normally; they
do not need to know or type a skill name. When no workflow is named, use
`adaptive-workflow` to select the smallest useful ordered set. Read only the selected
skills and relevant references. State the selected workflow briefly so its effect is
visible, then continue without asking the user to approve an internal routing choice.

Route by outcome and consequence:

- **High confidence:** announce the workflow in one short sentence and continue.
- **Several materially different outcomes:** show two or three plain-language
  choices, put the recommended outcome first, and wait for the user's selection.
- **Missing information blocks safe progress:** ask one concise question and continue
  useful read-only inspection when possible.

Prefer one primary skill and no more than two supporting skills. Do not run all skills
for every task. Preserve explicit boundaries such as diagnosis only, planning only,
or no source edits. A user-named skill overrides automatic routing; add another only
when it is necessary for the requested outcome.

| Request | Skill |
| --- | --- |
| Select and combine workflows from a natural-language task | `adaptive-workflow` |
| Implement, refactor, review, audit, or inventory technical debt | `lean-senior-engineering` |
| Investigate a bug, build error, or test failure | `systematic-debugging` |
| Verify a coding change before handoff | `verification-before-completion` |
| Clarify an ambiguous feature or consequential design decision | `feature-discovery` |
| Research or execute a substantial change across modules or sessions | `research-plan-implement` |
| Explain architecture, data processing, or impact with code evidence | `architecture-map` |
| Assess a release and its outstanding checks | `release-readiness` |
| Reproduce a web UI issue using browser evidence | `browser-diagnostics` |

Keep investigation and testing proportional. Reuse existing project commands and
patterns. A simple fix can use debugging and focused verification without generating
a specification or repository map. A diagnosis or review request produces findings
unless changes are also requested. Do not show skill-name choices when outcome-based
labels such as **Diagnose only** or **Fix and verify** are clearer to the user.

Explicit user choices and this repository's specific conventions take precedence over skill defaults. Continue work already authorized; do not create extra approval steps. Report actual checks and material limitations. Do not invent unavailable tools, completed tests, or runtime evidence.
