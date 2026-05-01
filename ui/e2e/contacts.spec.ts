import { expect, test } from '@playwright/test'

test.describe('Contacts page', () => {
  test('selects a department from the SVG map and renders TCI/TCS/Solution', async ({ page }) => {
    await page.goto('/contacts')

    // The SVG map renders a marker per metropole department. Click "69" (Rhône).
    await page.getByTestId('france-map-69').click()
    await expect(page.getByTestId('france-map-69')).toHaveAttribute('aria-pressed', 'true')

    // The right column resolves contacts for department 69.
    await expect(page.getByRole('heading', { name: /69 · Rhône/ })).toBeVisible()
    await expect(page.getByRole('heading', { name: /^TCI$/ })).toBeVisible()
    await expect(page.getByRole('heading', { name: /^TCS$/ })).toBeVisible()
    await expect(page.getByRole('heading', { name: /Solution Habitat/ })).toBeVisible()
    await expect(page.getByText(/c\.durand@france-air\.com/)).toBeVisible()
  })

  test('opens the new-client modal and persists a created client', async ({ page }) => {
    await page.goto('/contacts')

    await page.getByTestId('open-new-client').click()
    const dialog = page.getByRole('dialog', { name: /ajouter un nouveau client/i })
    await expect(dialog).toBeVisible()

    await dialog.getByLabel(/code client/i).fill('e2e-001')
    await dialog.getByLabel(/nom du client/i).fill('Cabinet E2E')
    await dialog.getByLabel(/code postal/i).fill('69001')
    // Department auto-derived. Submit.
    await dialog.getByRole('button', { name: /créer le client/i }).click()

    await expect(dialog).toBeHidden({ timeout: 5000 })
    await expect(page.getByText('Cabinet E2E')).toBeVisible()
    await expect(page.getByTestId('france-map-69')).toHaveAttribute('aria-pressed', 'true')
  })
})
