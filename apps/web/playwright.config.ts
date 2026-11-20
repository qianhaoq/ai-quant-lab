import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry"
  },
  webServer: [
    {
      command: "cd ../api && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
      env: {
        API_TOKENS: '{"fake-e2e-token":"local-operator"}',
        BROKER_OWNER_SUBJECT: "local-operator",
        BROKER_ACCOUNT_ID: "internal-sandbox",
        BROKER_PROVIDER: "internal_sandbox",
        BROKER_MODE: "sandbox",
        ENABLE_LIVE_TRADING: "false",
        ENABLE_PAID_MODELS: "false",
        OPENAI_API_KEY: "",
        ALPACA_API_KEY_ID: "",
        ALPACA_API_SECRET_KEY: "",
        SAFETY_DB_PATH: `.local/e2e-${Date.now()}.sqlite3`
      },
      port: 8000,
      reuseExistingServer: false
    },
    {
      command: "pnpm dev",
      port: 3000,
      reuseExistingServer: true
    }
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
