import { defineConfig, devices } from "@playwright/test";
import path from "path";

export default defineConfig({
  testDir: path.join(__dirname, "e2e"),
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: true,
  workers: 2,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000",
      cwd: path.join(__dirname, "..", "backend"),
      port: 8000,
      reuseExistingServer: true,
      env: {
        POSTGRES_DSN: "sqlite+aiosqlite:///./e2e.db",
        FRONTEND_URL: "http://localhost:3000",
        BACKEND_URL: "http://localhost:8000",
        JWT_SECRET_KEY: "playwright-secret",
      },
      timeout: 60_000,
    },
    {
      command: "npm run start",
      cwd: __dirname,
      port: 3000,
      reuseExistingServer: true,
      env: {
        NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000",
        NEXT_PUBLIC_WS_BASE_URL: "ws://localhost:8000",
      },
      timeout: 60_000,
    },
  ],
});
