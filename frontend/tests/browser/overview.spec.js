import { test, expect } from '@playwright/test'

test('real FastAPI data, details, keyboard navigation and local requests', async ({ page }) => {
  const requests = [], errors = []
  page.on('request', request => requests.push(request.url()))
  page.on('pageerror', error => errors.push(error.message))
  const profile = await (await page.request.get('/api/profile/ASTRO-001')).json()
  const drifts = await (await page.request.get('/api/drift/ASTRO-001')).json()
  const event = drifts.toSorted((a,b) => a.detected_at.localeCompare(b.detected_at) || a.id.localeCompare(b.id)).at(-1)
  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('lang', 'fr')
  await expect(page.getByRole('heading', { name: new RegExp(profile.first_name) })).toBeVisible()
  await expect(page.locator('.presence--drift')).toBeVisible()
  await page.getByRole('button', { name: 'Pourquoi ?' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.locator('#drift-explanation')).toContainText(event.explanation)
  await expect(page.locator('.drift-tag')).toHaveText(`${Math.round(event.drift_score * 100)} % · écart par rapport à ton rythme habituel`)
  await expect(page.getByRole('heading', { name: 'Sommeil' })).toBeVisible()
  await expect(page.locator('body')).not.toContainText(/\b(moderate|Overview|Show me why|diagnostic|maladie|risque psychologique|alerte critique)\b/i)
  await page.getByRole('button', { name: 'Moins de détails' }).click()
  await page.screenshot({ path: 'test-results/overview-desktop.png', fullPage: true })
  for (const name of ['Mémoire', 'Accompagnement']) {
    await page.getByRole('link', { name, exact: true }).click()
    await expect(page.getByRole('heading', { name: name + '.', exact: true })).toBeVisible()
    await expect(page.getByText('UN ESPACE PREND FORME')).toBeVisible()
  }
  expect(errors).toEqual([])
  expect(requests.every(url => new URL(url).hostname === '127.0.0.1')).toBeTruthy()
})

test('tablets and mobile remain usable, reduced motion is honored', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  for (const width of [768, 390]) {
    await page.setViewportSize({ width, height: 1024 })
    await page.goto('/')
    await expect(page.getByRole('button', { name: 'Pourquoi ?' })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
    expect(await page.locator('.presence-body').evaluate(el => getComputedStyle(el).animationName)).toBe('none')
    await expect(page.getByRole('link', { name: 'Compagnon', exact: true })).toBeVisible()
    await page.screenshot({ path: `test-results/overview-${width}.png`, fullPage: true })
  }
})

test('unavailable core and retry never expose technical errors', async ({ page }) => {
  await page.route('**/api/**', route => route.fulfill({ status: 503, body: 'Internal connection failure' }))
  await page.goto('/')
  await expect(page.getByText('Le cœur de PsychoSpace est momentanément indisponible.')).toBeVisible()
  await expect(page.getByText('Internal connection failure')).toHaveCount(0)
  await page.unroute('**/api/**')
  await page.getByRole('button', { name: 'Réessayer' }).click()
  await expect(page.getByRole('button', { name: 'Pourquoi ?' })).toBeVisible()
})

test('missing data stays empty, no fabricated assessment', async ({ page }) => {
  await page.route('**/api/baseline/**', route => route.fulfill({ status: 404, body: '{}' }))
  for (const resource of ['drift', 'checkins']) await page.route(`**/api/${resource}/**`, route => route.fulfill({ json: [] }))
  await page.goto('/')
  await expect(page.getByText('Un moment pour retrouver ton rythme.')).toBeVisible()
  await expect(page.getByText('Ton rythme habituel n’est pas encore disponible.')).toBeVisible()
  await expect(page.locator('.presence--idle')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Pourquoi ?' })).toHaveCount(0)
  await page.route('**/api/profile/**', route => route.fulfill({ status: 404, body: '{}' }))
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Ton espace t’attend.' })).toBeVisible()
})

test('loading state is visible while data is pending', async ({ page }) => {
  let release
  const waiting = new Promise(resolve => { release = resolve })
  await page.route('**/api/**', async route => { await waiting; await route.continue() })
  await page.goto('/')
  await expect(page.getByRole('status')).toContainText('Ton espace se prépare.')
  release()
  await expect(page.getByRole('button', { name: 'Pourquoi ?' })).toBeVisible()
})
