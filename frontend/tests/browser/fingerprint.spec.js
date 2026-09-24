import { test, expect } from '@playwright/test'
import { fingerprintData } from '../../src/fingerprint.js'
import { latest } from '../../src/overview.js'
import { fullDate, metricValue } from '../../src/evolution.js'

async function open(page) {
  await page.goto('/#evolution')
  await page.getByRole('button', { name: 'Empreinte de rythme', exact: true }).click()
}

test('real detection footprint reads three APIs, excludes April 16, exposes original values and signals', async ({ page }) => {
  const [checkins, baseline, drifts] = await Promise.all(['checkins', 'baseline', 'drift'].map(async resource => (await page.request.get(`/api/${resource}/ASTRO-001`)).json()))
  const drift = latest(drifts, 'detected_at'), data = fingerprintData(checkins, baseline, drift)
  expect(data.records.map(record => record.timestamp.slice(0, 10))).toEqual(['2080-04-13', '2080-04-14', '2080-04-15'])
  const requests = []
  await page.goto('/#evolution')
  await expect(page.locator('#selected-day-title')).toBeVisible()
  page.on('request', request => { if (request.url().includes('/api/')) requests.push(request) })
  await page.getByRole('button', { name: 'Empreinte de rythme', exact: true }).click()
  await expect(page.locator('.fingerprint-moment h2')).toContainText(fullDate(drift.detected_at))
  await expect(page.locator('.fingerprint-window').first()).toContainText('13 avril 2080 au 15 avril 2080')
  for (const value of data.values) {
    const button = page.locator('.fingerprint-dimensions button').filter({ hasText: value.label })
    await button.focus(); await page.keyboard.press('Enter')
    await expect(button).toHaveAttribute('aria-pressed', 'true')
    await expect(page.locator('[data-value="usual"]')).toHaveText(metricValue(value, value.usual))
    await expect(page.locator('[data-value="recent"]')).toHaveText(metricValue(value, value.recent))
    await expect(page.locator(`[data-signal="${value.key}"]`)).toHaveCount(value.affected ? 1 : 0)
  }
  await page.getByText('Pourquoi ?', { exact: true }).click()
  await expect(page.locator('.fingerprint-moment')).toContainText(drift.explanation)
  await expect(page.locator('.fingerprint-moment')).toContainText('Indice d’évolution : 62 %')
  expect([...new Set(requests.map(request => new URL(request.url()).pathname))].sort()).toEqual(['/api/baseline/ASTRO-001', '/api/checkins/ASTRO-001', '/api/drift/ASTRO-001'])
  expect(requests.every(request => request.method() === 'GET')).toBeTruthy()
  await expect(page.locator('.fingerprint')).not.toContainText(/DRIFT-002|moderate|affected_signals|2080-04-15T/)
  await page.getByRole('button', { name: 'Voir le changement', exact: true }).click()
  await expect(page.getByRole('status')).toHaveText('Le contour récent se dessine…')
  await expect(page.locator('.fingerprint-recent')).toHaveAttribute('data-progress', '1')
  await page.getByRole('button', { name: 'Revenir à la comparaison' }).click()
  await page.screenshot({ path: 'test-results/fingerprint-desktop.png', fullPage: true })
  console.log('Fenêtre réelle :', data.records.map(record => record.timestamp), 'Comparaisons :', data.values.map(value => ({ dimension: value.label, habituel: value.usual, recent: value.recent })))
})

test('tablet and mobile keep controls and comparison accessible with reduced motion', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await open(page)
  for (const width of [768, 390]) {
    await page.setViewportSize({ width, height: 1000 })
    await page.getByRole('button', { name: 'Voir le changement', exact: true }).click()
    await expect(page.locator('.fingerprint-recent')).toHaveAttribute('data-progress', '1')
    await expect(page.getByRole('status')).toHaveText('Les deux empreintes sont superposées.')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
    expect(await page.locator('.fingerprint .presence-body').evaluate(el => getComputedStyle(el).animationName)).toBe('none')
    await page.screenshot({ path: `test-results/fingerprint-${width}.png`, fullPage: true })
  }
  await page.getByRole('button', { name: 'Trace dans le temps' }).click()
  await expect(page.locator('#selected-day-title')).toContainText('16 avril 2080')
})

test('empty data and API failure never fabricate an imprint and retry recovers', async ({ page }) => {
  await page.route('**/api/checkins/**', route => route.fulfill({ json: [] }))
  await open(page)
  await expect(page.getByText('Il me faut encore quelques bilans pour comparer ton rythme.')).toBeVisible()
  await expect(page.locator('.fingerprint-recent')).toHaveCount(0)
  await page.route('**/api/checkins/**', route => route.fulfill({ status: 503, body: 'Internal error' }))
  await page.getByRole('button', { name: 'Trace dans le temps' }).click()
  await page.getByRole('button', { name: 'Empreinte de rythme', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Je n’arrive pas à reconstruire cette évolution pour le moment.')
  await page.unroute('**/api/checkins/**')
  await page.getByRole('button', { name: 'Réessayer' }).click()
  await expect(page.locator('.fingerprint-recent')).toBeVisible()
})

test('loading is explicit and missing baseline stays insufficient', async ({ page }) => {
  let release
  const pending = new Promise(resolve => { release = resolve })
  await page.route('**/api/baseline/**', async route => { await pending; await route.fulfill({ status: 404, body: '{}' }) })
  await open(page)
  await expect(page.getByRole('status')).toContainText('PsychoSpace reconstitue ton empreinte...')
  release()
  await expect(page.getByText('Il me faut encore quelques bilans pour comparer ton rythme.')).toBeVisible()
})
