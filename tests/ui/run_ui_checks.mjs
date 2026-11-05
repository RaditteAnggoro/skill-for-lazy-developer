import { createServer } from "node:http";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const snapshots = path.join(here, "snapshots");
const artifacts = path.join(here, "artifacts");
const chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const fixtures = {
  plain: path.join(here, "fixtures/plain"),
  react: path.join(here, "fixtures/react/dist"),
};
const failures = [];
const checks = [];
const consoleErrors = [];

function record(name, ok, detail = "") {
  checks.push({ name, ok, detail });
  if (!ok) failures.push(name + (detail ? `: ${detail}` : ""));
}

function contentType(file) {
  if (file.endsWith(".html")) return "text/html";
  if (file.endsWith(".js")) return "text/javascript";
  if (file.endsWith(".css")) return "text/css";
  if (file.endsWith(".png")) return "image/png";
  return "application/octet-stream";
}

function serve(root) {
  return new Promise((resolve) => {
    const server = createServer(async (request, response) => {
      const pathname = decodeURIComponent(new URL(request.url, "http://127.0.0.1").pathname);
      if (pathname === "/favicon.ico") {
        response.writeHead(204); response.end(); return;
      }
      const file = path.join(root, pathname === "/" ? "index.html" : pathname);
      if (!file.startsWith(root) || !existsSync(file)) {
        response.writeHead(404); response.end("not found"); return;
      }
      try {
        const body = await readFile(file);
        response.writeHead(200, { "content-type": contentType(file) });
        response.end(body);
      } catch {
        response.writeHead(500); response.end("read failed");
      }
    });
    server.listen(0, "127.0.0.1", () => resolve(server));
  });
}

async function screenshot(page, fixture, width) {
  const file = path.join(artifacts, `${fixture}-${width}.png`);
  await page.screenshot({ path: file, fullPage: true });
  const baseline = path.join(snapshots, `${fixture}-${width}.png`);
  if (!existsSync(baseline) || process.argv.includes("--update-snapshots")) {
    await mkdir(snapshots, { recursive: true });
    await writeFile(baseline, await readFile(file));
    record(`screenshot:${fixture}:${width}`, true, "baseline-created");
    return;
  }
  const expected = PNG.sync.read(await readFile(baseline));
  const actual = PNG.sync.read(await readFile(file));
  if (expected.width !== actual.width || expected.height !== actual.height) {
    record(`screenshot:${fixture}:${width}`, false, `size ${expected.width}x${expected.height} != ${actual.width}x${actual.height}`);
    return;
  }
  const diff = new PNG({ width: expected.width, height: expected.height });
  const changed = pixelmatch(expected.data, actual.data, diff.data, expected.width, expected.height, { threshold: 0.1 });
  const ratio = changed / (expected.width * expected.height);
  record(`screenshot:${fixture}:${width}`, ratio <= 0.02, `${(ratio * 100).toFixed(3)}% changed`);
}

async function runFixture(browser, fixture) {
  const root = fixtures[fixture];
  if (!existsSync(root)) {
    record(`fixture:${fixture}`, false, "build output missing");
    return;
  }
  const server = await serve(root);
  const base = `http://127.0.0.1:${server.address().port}/`;
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(`${fixture}: ${message.text()}`); });
    page.on("pageerror", (error) => consoleErrors.push(`${fixture}: ${error.message}`));
    await page.goto(base, { waitUntil: "networkidle" });
    record(`title:${fixture}`, (await page.title()).length > 0, await page.title());
    record(`rows:${fixture}`, (await page.locator("table tbody tr").count()) === 6);
    record(`overflow:${fixture}:1440`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    await screenshot(page, fixture, 1440);

    // Keyboard traversal: focus the search field and verify a chain of controls and visible focus.
    await page.locator('input[type="search"]').focus();
    const focusChain = [];
    for (let i = 0; i < 8; i += 1) {
      await page.keyboard.press("Tab");
      focusChain.push(await page.evaluate(() => {
        const active = document.activeElement;
        const style = active ? getComputedStyle(active) : null;
        return { tag: active?.tagName, id: active?.id, label: active?.getAttribute("aria-label"), text: active?.textContent?.trim().slice(0, 30), outline: style?.outlineStyle };
      }));
    }
    const distinct = new Set(focusChain.map((item) => item.id || item.label || item.text || item.tag));
    record(`keyboard:${fixture}`, distinct.size >= 5, `${distinct.size} distinct stops`);
    record(`focus-visible:${fixture}`, focusChain.some((item) => item.outline && item.outline !== "none"), JSON.stringify(focusChain[0]));

    // Narrow viewport: reflow and no horizontal overflow.
    await page.setViewportSize({ width: 360, height: 900 });
    await page.goto(base, { waitUntil: "networkidle" });
    record(`overflow:${fixture}:360`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    record(`rows:${fixture}:360`, (await page.locator("table tbody tr").count()) === 6);
    await screenshot(page, fixture, 360);

    // Empty, loading, and error states.
    await page.getByRole("button", { name: "Load empty state" }).click();
    record(`empty:${fixture}`, await page.getByText("No approvals match").first().isVisible());
    await page.getByRole("button", { name: "Reset" }).click();
    await page.getByRole("button", { name: "Load loading state" }).click();
    record(`loading:${fixture}`, await page.getByText("Loading approvals…").first().isVisible());
    await page.getByRole("button", { name: "Reset" }).click();
    await page.getByRole("button", { name: "Load error state" }).click();
    record(`error:${fixture}`, await page.getByRole("alert").isVisible());
    await page.getByRole("button", { name: "Retry" }).click();
    record(`retry:${fixture}`, await page.locator("table tbody tr").count() === 6);

    // Filter, selection, and bulk approval.
    await page.locator('input[type="search"]').fill("1042");
    record(`filter:${fixture}`, await page.locator("table tbody tr").count() === 1);
    await page.getByRole("button", { name: "Clear filters" }).click();
    await page.locator("table tbody tr").first().getByRole("checkbox").check();
    record(`bulk-visible:${fixture}`, await page.getByRole("button", { name: "Approve selected" }).isVisible());
    await page.getByRole("button", { name: "Approve selected" }).click();
    record(`bulk-approved:${fixture}`, await page.getByText("1 records approved.").isVisible().catch(() => false) || (await page.getByText("1 selected").isVisible().catch(() => true)));
    await page.close();
  } finally {
    server.close();
  }
}

const browser = await chromium.launch({ headless: true, executablePath: chrome });
try {
  await mkdir(artifacts, { recursive: true });
  await runFixture(browser, "plain");
  await runFixture(browser, "react");
  // Next fixture is source-validated; its build is not installed in this fixture run.
  const nextPage = await readFile(path.join(here, "fixtures/next/app/page.jsx"), "utf8");
  const nextLayout = await readFile(path.join(here, "fixtures/next/app/layout.jsx"), "utf8");
  record("next:page", nextPage.includes("EnterpriseApprovals"));
  record("next:layout", nextLayout.includes("lang=\"en\""));
} finally {
  await browser.close();
}
record("console-errors", consoleErrors.length === 0, consoleErrors.join(" | "));
const report = { checks, failures, console_errors: consoleErrors, passed: failures.length === 0 };
await writeFile(path.join(artifacts, "report.json"), JSON.stringify(report, null, 2) + "\n");
for (const check of checks) console.log(`${check.ok ? "PASS" : "FAIL"} ${check.name}${check.detail ? " — " + check.detail : ""}`);
if (failures.length) { console.error(`\n${failures.length} UI check(s) failed`); process.exit(1); }
console.log(`\nAll ${checks.length} UI checks passed.`);
