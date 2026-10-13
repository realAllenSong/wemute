import { defineConfig } from "@playwright/test";

const PORT = 4402;
const BASE_URL = `http://127.0.0.1:${PORT}`;

// Runs against the already-built site (`npm run build`); nothing is built here.
export default defineConfig({
  testDir: "e2e",
  testMatch: "**/*.spec.ts",
  globalSetup: "./e2e/global-setup.ts",
  outputDir: "test-results/e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  // FFmpeg runs on the CPU inside each tab; too many tabs make video jobs crawl.
  workers: process.env.E2E_WORKERS ? Number(process.env.E2E_WORKERS) : 4,
  timeout: 180_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [["list"], ["html", { open: "never", outputFolder: "test-results/e2e-report" }]] : "list",
  use: {
    baseURL: BASE_URL,
    channel: "chrome",
    headless: true,
    acceptDownloads: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    // --ignore-lock: run beside any preview server the developer already has open.
    command: `npx astro preview --host 127.0.0.1 --port ${PORT} --ignore-lock`,
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    stdout: "ignore",
    stderr: "pipe",
  },
});
