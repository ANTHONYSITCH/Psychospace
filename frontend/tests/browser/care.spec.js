import { test, expect } from '@playwright/test'
import { interventionLabel, interventionState, relevantIntervention } from '../../src/care.js'
import { missionTimestamp } from '../../src/utils/missionClock.js'
import { randomUUID } from 'node:crypto'

test('real API proposal and history, French labels, defer has no write', async ({ page }) => {
  const rows = await (await page.request.get('/api/interventions/ASTRO-001')).json()
  const chosen = relevantIntervention(rows)
  const writes = []
  page.on('request', request => { if (request.method() !== 'GET') writes.push(request.url()) })
  await page.goto('/#care')
  await expect(page.locator('.care-api-message')).toHaveText(chosen.message)
  await expect(page.locator('.care-state')).toHaveText(interventionState(chosen))
  await expect(page.locator('.care-proposal h3')).toHaveText(interventionLabel(chosen.type))
  await expect(page.locator('.care-history li')).toHaveCount(rows.length)
  await expect(page.locator('.care-page')).not.toContainText(/INT-|DRIFT-|quiet_time|calm_conversation|accepted|completed|prescription/i)
  if (!chosen.accepted) {
    await page.getByRole('button', { name: 'Pas maintenant' }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText('On peut y revenir plus tard.')).toBeVisible()
    await page.getByRole('button', { name: 'Retrouver cette proposition' }).click()
    await expect(page.locator('.care-api-message')).toHaveText(chosen.message)
  }
  expect(writes).toEqual([])
  await page.locator('h1').click()
  await page.screenshot({ path: 'test-results/care-desktop.png', fullPage: true })
})

test('real separate demonstration is accepted then completed through UI and GET', async ({ page }) => {
  test.skip(process.env.PSYCHOSPACE_REAL_CARE !== '1', 'Explicit real demonstration only')
  const before = await (await page.request.get('/api/interventions/ASTRO-001')).json()
  // Copy a real backend message, preserving the originals. No production creation UI.
  const source = relevantIntervention(before)
  const created = { ...source, id: `INT-DEMO-${randomUUID()}`, created_at: missionTimestamp(), accepted: false, completed: false }
  const post = await page.request.post('/api/interventions', { data: created })
  expect(post.status()).toBe(201)
  await page.goto('/#care')
  await expect(page.locator('.care-state')).toHaveText('Proposition')
  const accept = page.waitForResponse(response => response.url().endsWith(`/api/interventions/${created.id}`) && response.request().method() === 'PATCH')
  await page.getByRole('button', { name: 'Ça me va' }).click()
  const accepted = await accept
  expect(accepted.status()).toBe(200)
  expect(accepted.request().postDataJSON()).toEqual({ accepted: true })
  await expect(page.locator('.care-state')).toHaveText('En cours')
  const intermediate = await (await page.request.get('/api/interventions/ASTRO-001')).json()
  expect(intermediate.find(item => item.id === created.id)).toEqual({ ...created, accepted: true })
  const complete = page.waitForResponse(response => response.url().endsWith(`/api/interventions/${created.id}`) && response.request().method() === 'PATCH')
  await page.getByRole('button', { name: 'J’ai terminé', exact: true }).click()
  const completed = await complete
  expect(completed.status()).toBe(200)
  expect(completed.request().postDataJSON()).toEqual({ completed: true })
  await expect(page.locator('.care-state')).toHaveText('Terminé')
  await expect(page.getByRole('status')).toContainText('Merci de m’avoir tenu au courant.')
  const after = await (await page.request.get('/api/interventions/ASTRO-001')).json()
  expect(after.find(item => item.id === created.id)).toEqual({ ...created, accepted: true, completed: true })
  expect(after.filter(item => item.id !== created.id)).toEqual(before)
  console.log('Accompagnement réel :', created.id, 'accepted=true, completed=true confirmés par GET ; interventions originales intactes. Date :', created.created_at)
})

test('PATCH pending or failed preserves proposal, then confirmed transitions and double submit protection', async ({ page }) => {
  const rows = await (await page.request.get('/api/interventions/ASTRO-001')).json()
  const item = { ...rows.at(-1), accepted: false, completed: false }
  let release, fail = true, writes = 0
  const pending = new Promise(resolve => { release = resolve })
  await page.route('**/api/interventions/*', async route => {
    if (route.request().method() === 'GET') return route.fulfill({ json: [item] })
    writes++
    await pending
    if (fail) return route.fulfill({ status: 503, body: 'Raw internal error' })
    Object.assign(item, route.request().postDataJSON())
    await route.fulfill({ json: item })
  })
  await page.goto('/#care')
  await page.getByRole('button', { name: 'Ça me va' }).click()
  await expect(page.getByRole('button', { name: 'Ça me va' })).toBeDisabled()
  await expect(page.locator('.care-state')).toHaveText('Proposition')
  release()
  await expect(page.getByRole('alert')).toHaveText('Je n’ai pas réussi à enregistrer ton choix.')
  await expect(page.locator('.care-state')).toHaveText('Proposition')
  fail = false
  await page.getByRole('button', { name: 'Ça me va' }).evaluate(button => { button.click(); button.click() })
  await expect(page.locator('.care-state')).toHaveText('En cours')
  expect(writes).toBe(2)
  fail = true
  await page.getByRole('button', { name: 'J’ai terminé', exact: true }).click()
  await expect(page.getByRole('alert')).toHaveText('Je n’ai pas réussi à enregistrer ton choix.')
  await expect(page.locator('.care-state')).toHaveText('En cours')
  fail = false
  await page.getByRole('button', { name: 'J’ai terminé', exact: true }).click()
  await expect(page.locator('.care-state')).toHaveText('Terminé')
  await expect(page.locator('body')).not.toContainText('Raw internal error')
})

test('GET failure retry and empty state never create an intervention', async ({ page }) => {
  const writes = []
  page.on('request', request => { if (request.method() !== 'GET') writes.push(request.method()) })
  await page.route('**/api/interventions/*', route => route.fulfill({ status: 503, body: '{}' }))
  await page.goto('/#care')
  await expect(page.getByRole('alert')).toContainText('Je n’arrive pas à retrouver tes accompagnements pour le moment.')
  await page.route('**/api/interventions/*', route => route.fulfill({ json: [] }))
  await page.getByRole('button', { name: 'Réessayer' }).click()
  await expect(page.getByText('Rien à te proposer pour le moment.')).toBeVisible()
  await expect(page.getByText('PsychoSpace reste attentif à ton rythme.')).toBeVisible()
  expect(writes).toEqual([])
})

test('tablet and mobile keep proposal, keyboard history and reduced motion', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  for (const width of [768, 390]) {
    await page.setViewportSize({ width, height: 1000 })
    await page.goto('/#care')
    await expect(page.locator('.care-api-message')).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
    expect(await page.locator('.care-page .presence-body').evaluate(el => getComputedStyle(el).animationName)).toBe('none')
    await page.locator('.care-history button').last().focus()
    await page.keyboard.press('Enter')
    await expect(page.locator('.care-proposal h2')).toBeFocused()
    await page.screenshot({ path: `test-results/care-${width}.png`, fullPage: true })
  }
})
