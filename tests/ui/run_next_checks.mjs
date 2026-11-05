import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const nextDir = path.join(here, "fixtures/next");
const snapshots = path.join(here, "snapshots");
const artifacts = path.join(here, "artifacts");
const port = 3217;
const checks = [];
const failures = [];

function record(name, ok, detail = "") {
  checks.push({ name, ok, detail });
  if (!ok) failures.push(name + (detail ? `: ${detail}` : ""));
}

async function compare(page, width) {
  const actualPath = path.join(artifacts, `next-${width}.png`);
  await page.screenshot({ path: actualPath, fullPage: true });
  const baselinePath = path.join(snapshots, `next-${width}.png`);
  if (!existsSync(baselinePath) || process.argv.includes("--update-snapshots")) {
    await mkdir(snapshots, { recursive: true });
    await writeFile(baselinePath, await readFile(actualPath));
    record(`screenshot:next:${width}`, true, "baseline-created");
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

const server = spawn("npm", ["run", "start", "--", "-p", String(port)], {
  cwd: nextDir,
  env: { ...process.env, PORT: String(port) },
  stdio: ["ignore", "pipe", "pipe"],
});
let output = "";
server.stdout.on("data", (chunk) => { output += chunk; });
server.stderr.on("data", (chunk) => { output += chunk; });
const base = `http://127.0.0.1:${port}/`;
for (let attempt = 0; attempt < 60; attempt += 1) {
  try {
    const response = await fetch(base);
    if (response.ok) break;
  } catch {}
  await new Promise((resolve) => setTimeout(resolve, 250));
}

const browser = await chromium.launch({ headless: true, executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" });
try {
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
} finally {
  await browser.close();
  server.kill("SIGTERM");
}

record("next:server-output", !/error/i.test(output), output.slice(-300));
const report = { checks, failures, passed: failures.length === 0, server_output: output.slice(-3000) };
await writeFile(path.join(artifacts, "next-report.json"), JSON.stringify(report, null, 2) + "\n");
for (const check of checks) console.log(`${check.ok ? "PASS" : "FAIL"} ${check.name}${check.detail ? " — " + check.detail : ""}`);
if (failures.length) { console.error(`\n${failures.length} Next UI check(s) failed`); process.exit(1); }
console.log(`\nAll ${checks.length} Next UI checks passed.`);
