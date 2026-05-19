import { defineConfig, devices } from "@playwright/test";

// Set NO_PROXY so Playwright's URL probe and browser do not get hijacked by a
// local HTTP proxy (the dev machine has http_proxy=127.0.0.1:7890 in the env,
// which otherwise returns 502 for http://localhost:5173).
process.env.NO_PROXY = "localhost,127.0.0.1,::1";
process.env.no_proxy = "localhost,127.0.0.1,::1";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "vite --host 127.0.0.1 --port 5173",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
