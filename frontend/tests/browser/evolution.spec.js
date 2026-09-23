import { test, expect } from '@playwright/test'
import { dailyRecords, fullDate, metricValue, rhythmMetrics } from '../../src/evolution.js'
import { latest } from '../../src/overview.js'

test('real API trace, original values, baseline and actual detection date', async ({ page }) => {
  const [checkins, baseline, drifts] = await Promise.all(['checkins', 'baseline', 'drift'].map(async resource => (await page.request.get(`/api/${resource}/ASTRO-001`)).json()))
  const days = dailyRecords(checkins), last = days.at(-1), drift = latest(drifts, 'detected_at')
  const requests = []
  page.on('request', request => { if (request.url().includes('/api/')) requests.push(request) })
  await page.goto('/#evolution')
  await expect(page.locator('#selected-day-title')).toHaveText(fullDate(last.record.timestamp))
  expect(last.day).toBe('2080-04-16')
  for (const metric of rhythmMetrics) {
    const value = page.locator(`.day-values [data-metric="${metric.key}"]`)
    await expect(value.locator('dd')).toHaveText(metricValue(metric, last.record[metric.key]))
    await expect(value.locator('p')).toContainText(metricValue(metric, baseline[metric.baseline]))
  }
  await expect(page.locator('.detection-marker')).toHaveAttribute('data-detected-at', drift.detected_at)
  await page.locator('.detection-note summary').click()
  await expect(page.locator('.detection-note')).toContainText(drift.explanation)
  await expect(page.locator('.subtle-score')).toContainText('62 %')
  const earlier = days.find(day => day.day === '2080-04-14')
  await page.getByRole('button', { name: `Voir le ${fullDate(earlier.record.timestamp)}`, exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(page.locator('#selected-day-title')).toHaveText(fullDate(earlier.record.timestamp))
  await expect(page.locator('.day-values [data-metric="sleep_hours"] dd')).toHaveText(metricValue(rhythmMetrics[0], earlier.record.sleep_hours))
  await expect(page.locator('main')).not.toContainText(/DRIFT-002|moderate|Baseline|2080-04-15T|diagnostic/)
  expect([...new Set(requests.map(request => new URL(request.url()).pathname))].sort()).toEqual(['/api/baseline/ASTRO-001', '/api/checkins/ASTRO-001', '/api/drift/ASTRO-001'])
  expect(requests.every(request => request.method() === 'GET')).toBeTruthy()
  await page.screenshot({ path: 'test-results/evolution-desktop.png', fullPage: true })
})

test('narrow screens scroll the trace, retain real past records and honor reduced motion', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  for (const width of [768, 390]) {
    await page.setViewportSize({ width, height: 1024 })
    await page.goto('/#evolution')
    await expect(page.locator('#selected-day-title')).toContainText('16 avril 2080')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
    expect(await page.locator('.trace-scroll').evaluate(el => el.scrollWidth > el.clientWidth)).toBeTruthy()
    await page.getByRole('button', { name: 'Voir le 16 avril 2080', exact: true }).click()
    await page.screenshot({ path: `test-results/evolution-${width}.png`, fullPage: true })
    await page.getByLabel('Période', { exact: true }).selectOption('2026-09')
    await expect(page.locator('#selected-day-title')).toContainText('2026')
    await expect(page.locator('.detection-marker')).toHaveCount(0)
    await page.getByLabel('Période', { exact: true }).selectOption('2080-04')
  }
})

test('empty and failed responses remain human and retry works', async ({ page }) => {
  await page.route('**/api/checkins/**', route => route.fulfill({ json: [] }))
  await page.goto('/#evolution')
  await expect(page.getByText('Ton histoire commence avec tes prochains bilans.')).toBeVisible()
  await page.route('**/api/checkins/**', route => route.fulfill({ status: 503, body: 'Technical failure' }))
  await page.reload()
  await expect(page.getByRole('alert')).toContainText('Je n’arrive pas à retrouver ton évolution pour le moment.')
  await expect(page.locator('body')).not.toContainText('Technical failure')
  await page.unroute('**/api/checkins/**')
  await page.getByRole('button', { name: 'Réessayer' }).click()
  await expect(page.locator('#selected-day-title')).toContainText('2080')
})

test('pending requests and absent baseline do not invent comparative curves', async ({ page }) => {
  let release
  const pending = new Promise(resolve => { release = resolve })
  await page.route('**/api/baseline/**', async route => { await pending; await route.fulfill({ status: 404, body: '{}' }) })
  await page.goto('/#evolution')
  await expect(page.getByRole('status')).toContainText('PsychoSpace retrace ton évolution')
  release()
  await expect(page.locator('#selected-day-title')).toContainText('2080')
  await expect(page.getByText('Ta référence personnelle n’est pas encore disponible. Tes bilans restent consultables.')).toBeVisible()
  for (const path of await page.locator('path[data-metric]').all()) expect((await path.getAttribute('d')).trim()).toBe('')
  await expect(page.locator('.day-values')).not.toContainText('NaN')
})
