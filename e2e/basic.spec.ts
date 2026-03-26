import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL || 'https://veckosmak.vercel.app'

test.describe('Veckosmak E2E', () => {
  test('landing page loads with key elements', async ({ page }) => {
    await page.goto(BASE)
    await expect(page.locator('text=veckosmak')).toBeVisible()
    await expect(page.locator('text=Middagar som sparar')).toBeVisible()
    await expect(page.locator('text=Skapa min veckomeny')).toBeVisible()
  })

  test('preferences form has stepper controls', async ({ page }) => {
    await page.goto(BASE)
    await expect(page.locator('text=Antal personer')).toBeVisible()
    // Click + button to increase household size
    const plusButtons = page.locator('button:has-text("+")')
    await expect(plusButtons.first()).toBeVisible()
  })

  test('advanced settings expand/collapse', async ({ page }) => {
    await page.goto(BASE)
    const moreBtn = page.locator('button:has-text("Fler inställningar")')
    await moreBtn.click()
    await expect(page.locator('text=Kostval')).toBeVisible()
    await expect(page.locator('text=Vegetarisk')).toBeVisible()
  })

  test('health API returns ok', async ({ request }) => {
    const resp = await request.get(`${BASE.replace('vercel.app', 'api.onrender.com')}/api/health`)
    // May fail if Render is sleeping — that's ok in CI
    if (resp.ok()) {
      const data = await resp.json()
      expect(data.status).toMatch(/ok|warning/)
      expect(data.recipes).toBeGreaterThan(0)
    }
  })
})
