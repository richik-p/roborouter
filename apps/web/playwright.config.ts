import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";

const appRoot = __dirname;
const repositoryRoot = resolve(appRoot, "../..");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "uv run python scripts/run_e2e_api.py",
      cwd: repositoryRoot,
      env: { UV_CACHE_DIR: "/tmp/roborouter-e2e-uv-cache" },
      url: "http://127.0.0.1:8100/health",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "npm run build && npm run start -- --hostname 127.0.0.1 --port 3100",
      cwd: appRoot,
      env: { NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8100" },
      url: "http://127.0.0.1:3100",
      reuseExistingServer: false,
      timeout: 180_000,
    },
  ],
});
