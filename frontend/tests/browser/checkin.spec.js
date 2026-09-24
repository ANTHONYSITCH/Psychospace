import { test, expect } from '@playwright/test'

async function fillJourney(page) {
  await page.goto('/#pulse')
  await expect(page.getByRole('button', { name: 'Continuer' })).toBeDisabled()
  await page.getByRole('button', { name: '6 h 30', exact: true }).click()
  await page.getByRole('button', { name: 'Continuer' }).click()
  for (const value of [7, 3, 4, 6, 5]) {
    await page.getByRole('radio', { name: `${value} sur 10`, exact: true }).check()
    await page.getByRole('button', { name: 'Continuer' }).click()
  }
  await page.getByRole('spinbutton', { name: 'Durée en minutes' }).fill('37')
}

test('one question at a time, keyboard and back preserve answers', async ({ page }) => {
  await page.goto('/#pulse')
  await expect(page.locator('.presence--attentive')).toBeVisible()
  await page.getByRole('spinbutton').fill('25')
  await expect(page.getByRole('button', { name: 'Continuer' })).toBeDisabled()
  await page.getByRole('button', { name: '6 h 30' }).click()
  await page.getByRole('button', { name: 'Continuer' }).click()
  await expect(page.getByRole('radio')).toHaveCount(10)
  await expect(page.getByRole('spinbutton')).toHaveCount(0)
  await page.getByRole('radio', { name: '5 sur 10', exact: true }).focus()
  await page.keyboard.press('Space')
  await page.keyboard.press('ArrowRight')
  await expect(page.getByRole('radio', { name: '6 sur 10', exact: true })).toBeChecked()
  await page.getByRole('button', { name: 'Retour', exact: true }).click()
  await expect(page.getByRole('spinbutton')).toHaveValue('6.5')
  await page.getByRole('button', { name: 'Continuer' }).click()
  await expect(page.getByRole('radio', { name: '6 sur 10', exact: true })).toBeChecked()
  await page.screenshot({ path: 'test-results/checkin-desktop.png', fullPage: true })
})

test('failed save preserves responses, retry and double-click are controlled', async ({ page }) => {
  let calls = 0, release
  const gate = new Promise(resolve => { release = resolve })
  await page.route('**/api/checkins', async route => {
    calls++
    if (calls === 1) return route.fulfill({ status: 400, json: { detail: 'Technical validation details' } })
    await gate
    return route.fulfill({ status: 201, json: { success: true, checkin_id: 999 } })
  })
  await fillJourney(page)
  await page.getByRole('button', { name: 'Enregistrer mon état' }).click()
  await expect(page.getByRole('alert')).toContainText('Tes réponses sont conservées.')
  await expect(page.locator('body')).not.toContainText('Technical validation details')
  await page.getByRole('button', { name: 'Retour', exact: true }).click()
  await expect(page.getByRole('radio', { name: '5 sur 10', exact: true })).toBeChecked()
  await page.getByRole('button', { name: 'Continuer' }).click()
  await expect(page.getByRole('spinbutton')).toHaveValue('37')
  // Trigger two synchronous submits: the in-memory guard must reject the second.
  await page.locator('form').evaluate(form => { form.requestSubmit(); form.requestSubmit() })
  await expect(page.getByRole('button', { name: 'J’enregistre ton état…' })).toBeDisabled()
  await expect(page.getByRole('spinbutton')).toBeDisabled()
  await expect.poll(() => calls).toBe(2)
  release()
  await expect(page.getByText('Ton état du jour a bien été enregistré.')).toBeVisible()
  expect(calls).toBe(2)
})

test('tablet and mobile support the scale and reduced motion', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  for (const width of [768, 390]) {
    await page.setViewportSize({ width, height: 1024 })
    await page.goto('/')
    await page.goto('/#pulse')
    await page.getByRole('button', { name: '7 h', exact: true }).click()
    await page.getByRole('button', { name: 'Continuer' }).click()
    await page.getByRole('radio', { name: '10 sur 10', exact: true }).check()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
    expect(await page.locator('.presence-body').evaluate(el => getComputedStyle(el).animationName)).toBe('none')
    await page.screenshot({ path: `test-results/checkin-${width}.png`, fullPage: true })
  }
})

test('explicit real demonstration persists through FastAPI', async ({ page }) => {
  test.skip(process.env.PSYCHOSPACE_REAL_WRITE !== '1', 'Opt in explicitly: this demonstration creates a real check-in.')
  const before = await (await page.request.get('/api/checkins/ASTRO-001')).json()
  await fillJourney(page)
  const sent = page.waitForRequest(request => request.method() === 'POST' && request.url().endsWith('/api/checkins'))
  await page.getByRole('button', { name: 'Enregistrer mon état' }).click()
  const payload = (await sent).postDataJSON()
  await expect(page.getByText('Ton état du jour a bien été enregistré.')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Merci Alex.' })).toBeVisible()
  const after = await (await page.request.get('/api/checkins/ASTRO-001')).json()
  expect(after).toHaveLength(before.length + 1)
  expect(after).toContainEqual(payload)
  expect(payload.sleep_hours).toBe(6.5)
  expect(payload.activity_minutes).toBe(37)
  // Preserve real-clock coverage while validating the default mission-clock scenario.
  if (payload.timestamp.startsWith(`${new Date().getFullYear()}-`)) {
    expect(Math.abs(Date.now() - Date.parse(payload.timestamp))).toBeLessThan(30000)
  } else {
    expect(payload.timestamp).toMatch(/^2080-04-16T/)
    expect(Date.parse(payload.timestamp)).toBeGreaterThan(Date.parse('2080-04-15T23:59:59.999Z'))
    expect(after.at(-1)).toEqual(payload)
  }
  console.log('REAL_CHECKIN_PERSISTED', JSON.stringify(payload))
  await page.screenshot({ path: 'test-results/checkin-confirmation.png', fullPage: true })
  await page.getByRole('link', { name: 'Retour à la vue d’ensemble' }).click()
  await expect(page.getByRole('heading', { name: "Vue d'ensemble." })).toBeVisible()
  if (payload.timestamp.startsWith('2080-04-16')) {
    await expect(page.locator('.record-date')).toContainText('16 avr. 2080')
    await expect(page.locator('.metric').filter({ has: page.getByRole('heading', { name: 'Sommeil' }) }).locator('.metric-value')).toContainText('6,5')
    await expect(page.locator('.metric').filter({ has: page.getByRole('heading', { name: 'Activité' }) }).locator('.metric-value')).toContainText('37')
  }
})
