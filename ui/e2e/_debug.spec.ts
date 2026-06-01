import { test } from '@playwright/test'
test('debug home', async ({ page }) => {
  const errors: string[] = []
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()) })
  await page.goto('http://127.0.0.1:4173/')
  await page.waitForTimeout(3000)
  console.log('URL:', page.url())
  console.log('Content:', await page.content())
  console.log('Errors:', errors)
})
