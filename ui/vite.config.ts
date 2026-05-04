/// <reference types="vitest/config" />
import { defineConfig, type ProxyOptions } from 'vite'
import react from '@vitejs/plugin-react'

const BACKEND = 'http://127.0.0.1:8000'

// Proxy ONLY the backend HTTP API; SPA paths like /contacts, /options,
// /generate (which React Router owns) must fall through to index.html.
function backendProxy(): Record<string, string | ProxyOptions> {
  return {
    '^/parse/': BACKEND,
    '^/health$': BACKEND,
    '^/clients(/|$)': BACKEND,
    '^/contacts/department': BACKEND,
    '^/options(\\?|$)': BACKEND,
    '^/generate/(preview|pdf)': BACKEND,
    '^/admin/': BACKEND,
  }
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: backendProxy(),
  },
  preview: {
    port: 4173,
    proxy: backendProxy(),
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: true,
    // Vitest only owns src/test/**; e2e/ is exclusive to Playwright.
    include: ['src/test/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
  },
})
