import { defineConfig, devices } from '@playwright/test'

const PORT_FRONTEND = 4173
const PORT_BACKEND = 8000

const FRONTEND_URL = `http://127.0.0.1:${PORT_FRONTEND}`
const BACKEND_URL = `http://127.0.0.1:${PORT_BACKEND}`

const isCi = !!process.env.CI

export default defineConfig({
  testDir: './e2e',
  testIgnore: ['**/_*.spec.ts'],
  fullyParallel: false,
  retries: isCi ? 1 : 0,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 10_000 },

  reporter: isCi ? [['list'], ['html', { open: 'never' }]] : 'list',

  use: {
    baseURL: FRONTEND_URL,
    trace: 'retain-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: [
    {
      // Backend FastAPI - run from the repo root.
      command: `python -m uvicorn src.api.main:app --host 127.0.0.1 --port ${PORT_BACKEND}`,
      cwd: '..',
      url: `${BACKEND_URL}/health`,
      reuseExistingServer: !isCi,
      stdout: 'pipe',
      stderr: 'pipe',
      timeout: 60_000,
    },
    {
      // Production-style preview, served from the built UI bundle.
      command: `npm run build && npm run preview -- --host 127.0.0.1 --port ${PORT_FRONTEND} --strictPort`,
      url: FRONTEND_URL,
      reuseExistingServer: !isCi,
      stdout: 'pipe',
      stderr: 'pipe',
      timeout: 120_000,
    },
  ],
})
