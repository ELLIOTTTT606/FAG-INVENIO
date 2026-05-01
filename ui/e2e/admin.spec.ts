import { expect, test } from '@playwright/test'

test.describe('Admin / status', () => {
  test('Baserow badge in the header reads "mock" by default', async ({ page }) => {
    await page.goto('/')
    const badge = page.getByTestId('baserow-badge')
    await expect(badge).toBeVisible()
    await expect(badge).toHaveAttribute('data-mode', 'mock')
  })

  test('/admin/baserow-status returns a JSON payload', async ({ request }) => {
    const response = await request.get('/admin/baserow-status')
    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.mode).toMatch(/^(mock|live)$/)
    expect(body.tables).toBeDefined()
  })

  test('/health responds 200', async ({ request }) => {
    const response = await request.get('/health')
    expect(response.status()).toBe(200)
    expect(await response.json()).toEqual({ status: 'ok' })
  })
})
