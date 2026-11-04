# Validation scope

## Automated checks

Run `python scripts/validate_skills.py` after installing `requirements-dev.txt`.

The validator checks:

- Each skill has YAML frontmatter, a valid directory-matching name, a concise nonempty description, and a nonempty body.
- Skill metadata has no duplicate keys.
- UI metadata has a display name, a correctly sized description, a natural default
  prompt, and a valid optional implicit-invocation policy.
- Linked local files exist, stay inside the repository, and use portable links.
- GitHub workflow and issue-form YAML can be parsed.
- Routing cases reference installed skills, keep automatic chains small, avoid
  explicit skill-name syntax, and cover automatic, choice, and question interactions.

External URLs, Markdown anchors, model decisions, and application runtime behaviour are outside structural validation.

Run `python -m unittest discover -s tests -v` to test the validator and archive builder, including rejection of invalid metadata, missing references, and paths outside the repository.

The initial repository preparation passed 18 tooling tests locally on Python 3.9.6.
The original eight skills passed structure and local-link validation, and the
generated ZIP passed its integrity check. Hosted GitHub Actions had not yet run at
that point; the workflow is configured for Python 3.9 and 3.13.

The adaptive-routing increment adds a ninth skill and a natural-language routing
corpus in `tests/routing_cases.yaml`. Unit tests establish policy consistency and
fixture validity. They do not prove that every model, version, or surrounding prompt
will make the same semantic routing decision.

## Workflow trial

The initial pack was exercised on 2026-10-28 using a disposable Python pagination fixture. An independent agent read the implementation, debugging, and verification skills and received a request to fix a failing first-page test.

Observed results:

| Stage | Outcome |
| --- | --- |
| Existing baseline | 2 tests, first-page test failed |
| Expanded regression cases before fix | 6 tests, 4 failed |
| Focused offset fix | One implementation line changed |
| Verification after fix | 6 tests passed |

A separate independent file review examined all eight original skills and the initial
documentation. The resulting refinements clarified reuse of existing regression
tests, diagnosis-only source boundaries, and saved-artifact scope.

This trial does not establish behaviour across all models, codebases, or every workflow. Browser access, actual release execution, and hosted GitHub CI were not exercised by that trial. Report new evaluation results with the prompt, environment, expected behaviour, and observed evidence.

## Adaptive-routing trial

On 2026-11-04, four natural-language routing cases were run independently with
Codex CLI `0.166.0-alpha.5.1`, model `gpt-6.1-sol`, a read-only sandbox, the consuming
`AGENTS.md` snippet, and all nine skills copied into disposable directories. The
trials requested a route only; they did not execute or modify a project.

| Task shape | Expected interaction | Observed route |
| --- | --- | --- |
| Failing invoice unit test, fix requested | Automatic | `systematic-debugging` → `verification-before-completion` |
| “Improve the login experience” | Choice | Three outcome-based choices led by `feature-discovery` |
| Read-only campaign data-flow trace | Automatic | `architecture-map` only |
| Blank dashboard after browser refresh, fix requested | Automatic | `systematic-debugging` + `browser-diagnostics` → `verification-before-completion` |

All four successful reruns matched the requested interaction mode, kept the selected
set to three focused workflows or fewer, and preserved read-only boundaries. The
first harness attempt did not run because its strict output schema used an unsupported
`uniqueItems` keyword; the schema was corrected and the cases were rerun. That failed
harness attempt is not counted as a routing pass.

Final local maintenance checks validated all nine skills and local links, passed 26
unit tests, and built a reproducible 55-file release archive whose SHA-256 checksum
was verified. The workflow illustration was rendered in a local Chromium browser and
inspected at its native 1280 × 640 viewport.

These results establish only the observed routing behaviour for the stated CLI,
model, prompts, and instructions. They do not guarantee identical selection across
future models or additional repository context; `tests/routing_cases.yaml` is the
regression corpus to extend when a real routing miss is reported.
