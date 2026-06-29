import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright config for the CoachOwl web app.
 *
 * The `webServer` block boots the Vite dev server (`npm run dev`) and waits for
 * it to answer on http://localhost:5173 before any test runs. `reuseExistingServer`
 * lets you keep a dev server running locally and have the suite attach to it.
 *
 * The specs are self-contained: the activation flow stubs the API at the network
 * layer (see e2e/support/mockApi.ts), so no backend / Postgres is required for
 * `npm run test:e2e` to pass deterministically.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: false,
  // No flaky-retry masking locally — a green run means green.
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 120_000,
  },
})
