# Tool selection: capabilities before providers

Use this reference when a task benefits from an external service, a browser, a live
database, current documentation, or nontrivial code intelligence. User intent and
scope come first. Choose the work skill separately from tools; tools do not consume the
per-phase skill budget. Discover actual capabilities using the host's supported
mechanism, then use native tools when sufficient. A specialized tool can be the first
choice when it clearly provides better evidence or avoids redundant work. Do not launch
multiple heavyweight tools for the same evidence without a reason.

## Capability map

| Need | When a specialized capability helps | Native or existing fallback |
| --- | --- | --- |
| Code intelligence | Serena or another symbol index for cross-module references, inheritance, and complex impact | Repository search and source-backed caller tracing; disclose unresolved dynamic edges. |
| Library documentation | Context7 or authoritative docs for version-sensitive APIs, upgrades, and deprecations | Relevant repository docs; official documentation when needed. Never send private code or credentials to a docs service. |
| Browser journey | Playwright or equivalent for real interaction, responsive states, and regressions | Existing project browser tests or an available native browser. |
| Browser diagnosis | Chrome DevTools or equivalent for console, network, rendering, and performance evidence | Existing browser diagnostics or automation that captures the required evidence. Do not automatically run it alongside Playwright. |
| Database evidence | DBHub or equivalent for live schema, index, query-plan, or reconciliation evidence when needed | Inspect repository SQL and migrations; identify runtime evidence as unavailable. |
| Remote repository | GitHub MCP or equivalent for remote PRs, issues, and CI | Native Git for local status, diffs and history; another authorized remote interface when available. |

These are examples of capabilities, not guarantees of availability or a requirement to
use a named vendor. A server being listed does not establish that it works or is
authenticated. Distinguish available and working, registered but disconnected,
authentication required, disabled, unsupported, missing dependency, invocation failure,
and unknown. Check only what the task needs. Do not install, enable, configure,
authenticate, or remove servers as a side effect of discovery. On failure, use an
adequate native fallback; mark missing evidence blocked or unverified when no fallback
can provide it. Never claim a tool was used, a connection succeeded, or a check passed
without observed evidence.

Unknown means not yet verified, not unavailable: discover it when the task needs the
capability. If discovery cannot resolve the state, use an adequate fallback or report
the missing evidence rather than claiming the server is absent.

## Boundaries

- **Repository and documentation:** preserve diagnosis-only and analysis-only scope;
  treat indexes as navigation hints and verify anchors in source. Do not upload private
  source, credentials, or proprietary details to external services without authorization.
- **Browser:** use a development or authorized test environment and synthetic or
  approved accounts. Do not submit real transactions or send messages as a side effect
  of inspection. A screenshot or static analysis is not an executed user journey.
- **Database:** do not assume connectivity or connect to production automatically.
  Prefer sanitized development data and database-enforced read-only credentials; respect
  schema, row, and time limits. A client or MCP read-only flag alone is insufficient.
  Avoid unrestricted scans, sensitive data extraction and logging. Do not issue DDL,
  DML, transaction control, administrative operations, or potentially side-effecting
  procedures without separate authorization and safeguards. Treat EXPLAIN variants as
  potentially executing queries. Never weaken financial invariants or retry safety.
- **Remote operations:** local Git inspection is read-only; use authenticated remote
  capabilities only when needed. Pushing, merging, publishing or changing issues,
  settings, or external records requires the appropriate authorization.

Report what actually ran, which environment was used when material, and what remains
unverified. Provider capabilities, security boundaries and authentication vary by host;
this policy is guidance, not runtime enforcement.
