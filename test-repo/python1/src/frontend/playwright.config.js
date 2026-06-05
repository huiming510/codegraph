// Playwright E2E 配置
// 运行：npm run test:e2e 或 npx playwright test
const { defineConfig, devices } = require("@playwright/test");

const port = process.env.VITE_APP_PORT || 5174;
const baseURL = `http://localhost:${port}`;

module.exports = defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: "list",
  outputDir: "test-results",
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "on-first-retry"
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev",
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 60 * 1000
  }
});
