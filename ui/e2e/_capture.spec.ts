import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const SAMPLE_DOCX = path.resolve(__dirname, 'fixtures/sample_pac.docx')
const SHOTS = path.resolve(__dirname, '../screenshots')

test.describe('capture UI screenshots', () => {
  test.use({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  })

  test('captures every page of the app', async ({ page }) => {
    // 1. Home
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/01-home.png`, fullPage: true })

    // 2. Import (empty)
    await page.goto('/import')
    await expect(page.getByRole('button', { name: /déposer une fiche/i })).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/02-import-empty.png`, fullPage: true })

    // 3. Import (after parsing the DOCX)
    await page.locator('input[data-testid="dropzone-input"]').setInputFiles(SAMPLE_DOCX)
    await expect(page.getByRole('heading', { name: /PLP · 052 · HS/ })).toBeVisible({ timeout: 15_000 })
    await page.waitForTimeout(300)
    await page.screenshot({ path: `${SHOTS}/03-import-summary.png`, fullPage: true })

    // 4. Options (catalog loaded + a few selected via pre-checking)
    await page.getByRole('link', { name: /choisir les options/i }).click()
    await expect(page).toHaveURL(/\/options/)
    await expect(page.getByText(/option\(s\) sélectionnée\(s\)/i)).toBeVisible({ timeout: 10_000 })
    // Tick the first 2 options for visual interest.
    const checkboxes = page.locator('input[type="checkbox"]')
    const first = await checkboxes.first()
    await first.check()
    await page.waitForTimeout(150)
    await page.screenshot({ path: `${SHOTS}/04-options.png`, fullPage: true })

    // 5. Contacts (pick department 69, open SVG map highlight)
    await page.goto('/contacts')
    await expect(page.getByTestId('france-map')).toBeVisible()
    await page.getByTestId('france-map-69').click()
    await expect(page.getByRole('heading', { name: /69 · Rhône/ })).toBeVisible()
    await page.waitForTimeout(300)
    await page.screenshot({ path: `${SHOTS}/05-contacts.png`, fullPage: true })

    // 6. New-client modal open
    await page.getByTestId('open-new-client').click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/06-new-client-modal.png`, fullPage: true })
    await page.keyboard.press('Escape')
    // Closing via the cancel button to make sure the dialog goes away cleanly.
    await page.getByRole('button', { name: /annuler/i }).click().catch(() => undefined)

    // 7. Generate (preview iframe)
    await page.goto('/generate')
    await expect(page.getByTestId('preview-frame')).toBeVisible({ timeout: 15_000 })
    await page.waitForTimeout(500)
    await page.screenshot({ path: `${SHOTS}/07-generate-preview.png`, fullPage: true })
  })
})
