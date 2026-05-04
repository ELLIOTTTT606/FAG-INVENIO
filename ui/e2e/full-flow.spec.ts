import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const SAMPLE_DOCX = path.resolve(__dirname, 'fixtures/sample_pac.docx')

test.describe('happy path: import -> options -> contacts -> generate', () => {
  test('produces a valid PDF file at the end of the flow', async ({ page }) => {
    // 1. Home: CTA navigates to /import.
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await page.getByRole('link', { name: /générer ma fiche/i }).click()
    await expect(page).toHaveURL(/\/import$/)

    // 2. Import: drop the DOCX, see the extracted summary.
    await page.locator('input[data-testid="dropzone-input"]').setInputFiles(SAMPLE_DOCX)
    await expect(
      page.getByRole('heading', { name: /PLP · 052 · HS/ }),
    ).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('41.7 kW')).toBeVisible()

    // 3. Continue to options.
    await page.getByRole('link', { name: /choisir les options/i }).click()
    await expect(page).toHaveURL(/\/options/)
    await expect(page.getByText(/option\(s\) sélectionnée\(s\)/i)).toBeVisible({ timeout: 10_000 })
    // Pick the first available option.
    const firstCheckbox = page.locator('input[type="checkbox"]').first()
    await firstCheckbox.check()

    await page.getByRole('link', { name: /continuer vers la génération/i }).click()
    await expect(page).toHaveURL(/\/generate/)

    // 4. Generation: preview iframe + PDF download.
    await expect(page.getByTestId('preview-frame')).toBeVisible({ timeout: 15_000 })

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('download-pdf').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/^INVENIO-plp-052-hs\.pdf$/)
    const stream = await download.createReadStream()
    expect(stream).not.toBeNull()
    const chunks: Buffer[] = []
    if (stream) {
      for await (const chunk of stream) {
        chunks.push(Buffer.from(chunk))
      }
    }
    const buffer = Buffer.concat(chunks)
    expect(buffer.length).toBeGreaterThan(1000)
    // PDF magic bytes.
    expect(buffer.slice(0, 4).toString('ascii')).toBe('%PDF')
  })
})
