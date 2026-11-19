import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const nextDir = path.join(here, "fixtures/next");
const snapshots = path.join(here, "snapshots");
const artifacts = path.join(here, "artifacts");
const port = Number(process.env.UI_NEXT_PORT || 3217);
const checks = [];
const failures = [];

function record(name, ok, detail = "") {
  checks.push({ name, ok, detail });
  if (!ok) failures.push(name + (detail ? `: ${detail}` : ""));
}

async function compare(page, width) {
  const actualPath = path.join(artifacts, `next-${width}.png`);
  await page.screenshot({ path: actualPath, fullPage: true });
  if (process.env.UI_SNAPSHOT_MODE === "structural") {
    record(`screenshot:next:${width}`, true, "captured; pixel comparison disabled by UI_SNAPSHOT_MODE");
    return;
  }
  const baselinePath = path.join(snapshots, `next-${width}.png`);
  const update = process.argv.includes("--update-snapshots");
  if (!existsSync(baselinePath)) {
    if (!update) {
      record(`screenshot:next:${width}`, false, "baseline missing; run with --update-snapshots and review the diff");
      return;
    }
    await mkdir(snapshots, { recursive: true });
    await writeFile(baselinePath, await readFile(actualPath));
    record(`screenshot:next:${width}`, true, "baseline-updated explicitly; review before commit");
    return;
  }
  if (update) {
    await writeFile(baselinePath, await readFile(actualPath));
    record(`screenshot:next:${width}`, true, "baseline-updated explicitly; review before commit");
    return;
  }
  const expected = PNG.sync.read(await readFile(baselinePath));
  const actual = PNG.sync.read(await readFile(actualPath));
  if (expected.width !== actual.width || expected.height !== actual.height) {
    record(`screenshot:next:${width}`, false, "size mismatch");
    return;
  }
  const diff = new PNG({ width: expected.width, height: expected.height });
  const changed = pixelmatch(expected.data, actual.data, diff.data, expected.width, expected.height, { threshold: 0.1 });
  record(`screenshot:next:${width}`, changed / (expected.width * expected.height) <= 0.02, `${changed} pixels changed`);
}

if (!existsSync(path.join(nextDir, ".next"))) {
  console.error("Next fixture is not built. Run npm install && npm run build in tests/ui/fixtures/next.");
  process.exit(1);
}

function browserExecutable() {
  const configured = process.env.UI_BROWSER_EXECUTABLE;
  if (configured && existsSync(configured)) return configured;
  const candidates = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
  ];
  const found = candidates.find((candidate) => existsSync(candidate));
  if (found) return found;
  const bundled = chromium.executablePath();
  return bundled && existsSync(bundled) ? bundled : null;
}
const executable = browserExecutable();
if (!executable) {
  console.error("No Chrome/Chromium executable found. Set UI_BROWSER_EXECUTABLE or install Playwright Chromium.");
  process.exit(1);
}
const fixtureRequire = createRequire(path.join(nextDir, "package.json"));
const nextCli = fixtureRequire.resolve("next/dist/bin/next");
// Run Next directly so terminating this child also closes the server's output pipes.
const server = spawn(process.execPath, [nextCli, "start", "--hostname", "127.0.0.1", "--port", String(port)], {
  cwd: nextDir,
  stdio: ["ignore", "pipe", "pipe"],
});
const serverClosed = new Promise((resolve) => server.once("close", resolve));
let serverError;
server.once("error", (error) => { serverError = error; });
let output = "";
server.stdout.on("data", (chunk) => { output += chunk; });
server.stderr.on("data", (chunk) => { output += chunk; });
const base = `http://127.0.0.1:${port}/`;

async function waitForServer() {
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    if (serverError) throw serverError;
    if (server.exitCode !== null || server.signalCode !== null) break;
    try {
      const response = await fetch(base, { signal: AbortSignal.timeout(500) });
      await response.body?.cancel();
      if (response.ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Next fixture did not become ready.\n${output.slice(-3000)}`);
}

let browser;
try {
  await waitForServer();
  browser = await chromium.launch({ headless: true, executablePath: executable });
  await mkdir(artifacts, { recursive: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(base, { waitUntil: "networkidle" });
  record("next:rows", (await page.locator("table tbody tr").count()) === 6);
  record("next:overflow:1440", await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  await page.locator('input[type="search"]').focus();
  const chain = [];
  for (let i = 0; i < 8; i += 1) {
    await page.keyboard.press("Tab");
    chain.push(await page.evaluate(() => {
      const active = document.activeElement;
      return { id: active?.id, text: active?.textContent?.trim().slice(0, 30), tag: active?.tagName, label: active?.getAttribute("aria-label"), outline: getComputedStyle(active).outlineStyle };
    }));
  }
  record("next:keyboard", new Set(chain.map((item) => item.id || item.text || item.label || item.tag)).size >= 5);
  record("next:focus-visible", chain.some((item) => item.outline !== "none"));
  await compare(page, 1440);

  await page.setViewportSize({ width: 360, height: 900 });
  await page.goto(base, { waitUntil: "networkidle" });
  record("next:overflow:360", await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  await compare(page, 360);

  await page.getByRole("button", { name: "Load empty state" }).click();
  record("next:empty", await page.getByText("No approvals match").first().isVisible());
  await page.getByRole("button", { name: "Reset" }).click();
  await page.getByRole("button", { name: "Load loading state" }).click();
  record("next:loading", await page.getByText("Loading approvals…").first().isVisible());
  await page.getByRole("button", { name: "Reset" }).click();
  await page.getByRole("button", { name: "Load error state" }).click();
  record("next:error", await page.locator('.ea-state[role="alert"]').isVisible());
  await page.getByRole("button", { name: "Retry" }).click();
  await page.locator('input[type="search"]').fill("1042");
  record("next:filter", (await page.locator("table tbody tr").count()) === 1);
  await page.getByRole("button", { name: "Clear filters" }).click();
  await page.locator("table tbody tr").first().getByRole("checkbox").check();
  await page.getByRole("button", { name: "Approve selected" }).click();
  const bodyText = await page.locator("body").textContent();
  record("next:bulk-approved", bodyText.includes("1 records approved."), "explicit success message");
  record("next:bulk-state", (await page.locator("table tbody tr").first().textContent()).includes("approved"));
} finally {
  try {
    await browser?.close();
  } finally {
    server.kill("SIGTERM");
    const forceExit = setTimeout(() => server.kill("SIGKILL"), 5_000);
    try {
      await serverClosed;
    } finally {
      clearTimeout(forceExit);
    }
  }
}

record("next:server-output", !/error/i.test(output), output.slice(-300));
const report = { checks, failures, passed: failures.length === 0, server_output: output.slice(-3000) };
await writeFile(path.join(artifacts, "next-report.json"), JSON.stringify(report, null, 2) + "\n");
for (const check of checks) console.log(`${check.ok ? "PASS" : "FAIL"} ${check.name}${check.detail ? " — " + check.detail : ""}`);
if (failures.length) { console.error(`\n${failures.length} Next UI check(s) failed`); process.exit(1); }
console.log(`\nAll ${checks.length} Next UI checks passed.`);
