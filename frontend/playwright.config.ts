import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

// Repo-relative so the config works from any checkout; override the backend
// interpreter with E2E_PYTHON where the repo venv does not exist (e.g. CI).
const REPO_ROOT = path.resolve(__dirname, "..");
const E2E_SERVER = path.join(
  REPO_ROOT,
  "backend",
  "tests",
  "scripts",
  "e2e_server.py",
);
const VENV_PYTHON =
  process.env.E2E_PYTHON ?? path.join(REPO_ROOT, "backend", ".venv", "bin", "python");

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  retries: 0,
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `PORTAL_DB_PATH=/tmp/portal-e2e.db PORTAL_JWT_SECRET=${"e2e-secret-key-with-at-least-32-bytes-0123456789"} ${VENV_PYTHON} ${E2E_SERVER}`,
      url: "http://localhost:8001/api/professors",
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: "NEXT_PUBLIC_API_URL=http://localhost:8001 npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});