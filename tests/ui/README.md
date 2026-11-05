# UI fixture checks

These fixtures exercise the enterprise data profiles: dense approvals, filters,
selection, keyboard order, responsive table-to-card reflow, and empty/loading/error
states.

## Fixtures

- `fixtures/plain/index.html`: dependency-free HTML/CSS/JS.
- `fixtures/react`: Vite + React; build with `npm install && npm run build` in the fixture.
- `fixtures/next`: Next.js App Router (15.5.29); build with `npm install && npm run build`.
- `fixtures/shared/EnterpriseApprovals.jsx`: shared React implementation, copied into the
  Next fixture so each project remains self-contained.

## Run

```sh
cd tests/ui
npm install
npm run check
```

The runner starts a local static server, uses the installed Chrome, captures desktop and
mobile screenshots, compares them to `snapshots/`, and exercises keyboard, filter,
selection, bulk action, empty, loading, error, and retry paths. It does not require a
production connection.

For the built Next fixture:

```sh
cd tests/ui/fixtures/next
npm install
npm run build
cd ../..
npm run check:next
```

Use `node run_ui_checks.mjs --update-snapshots` only when an intentional visual change
requires new baselines. Screenshot baselines are tied to Chrome and the local font stack;
review the images before updating them.

## Limits

Automated checks do not replace an assistive-technology review or backend authorization
testing. The fixtures use test records only and make no production requests.
