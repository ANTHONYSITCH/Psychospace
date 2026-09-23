import { test, expect } from '@playwright/test'

const reply = { user_id: 'ASTRO-001', role: 'assistant', content: 'Prenons un moment au calme.', timestamp: '2080-04-16T12:00:01Z' }
function exchange(message) {
  return [{ id: 'TEST-USER', user_id: 'ASTRO-001', role: 'user', content: message, timestamp: '2080-04-16T12:00:00Z' }, { ...reply, id: 'TEST-REPLY' }]
}
async function emptyHistory(page) {
  await page.route('**/api/chat/ASTRO-001', route => route.fulfill({ json: [] }))
}

test('Companion loads real history, uses local requests and reveals only context categories', async ({ page }) => {
  const items = await (await page.request.get('/api/chat/ASTRO-001')).json()
  const external = []
  page.on('request', request => { if (new URL(request.url()).hostname !== '127.0.0.1') external.push(request.url()) })
  await page.goto('/')
  await page.getByRole('link', { name: 'Compagnon', exact: true }).click()
  await expect(page.locator('.transcript-entry')).toHaveCount(items.length)
  expect(await page.locator('.transcript-entry p').allTextContents()).toEqual(items.map(item => item.content))
  await expect(page.locator('.presence--attentive')).toBeVisible()
  await page.getByText('Ce que PsychoSpace utilise pour te répondre').click()
  await expect(page.getByText('Les souvenirs que tu as autorisés', { exact: true })).toBeVisible()
  await expect(page.getByText('Tu gardes le contrôle de ce que PsychoSpace mémorise.')).toBeVisible()
  await expect(page.locator('body')).not.toContainText(/drift_score|Memory IDs|Calling API|Generating tokens/)
  expect(external).toEqual([])
  await page.screenshot({ path: 'test-results/companion-desktop.png', fullPage: true })
})

test('empty state, keyboard input, thinking and long wait until real receipt', async ({ page }) => {
  await page.clock.install()
  let items = [], payload, release
  const gate = new Promise(resolve => { release = resolve })
  await page.route('**/api/chat/ASTRO-001', route => route.fulfill({ json: items }))
  await page.route('**/api/chat', async route => {
    payload = route.request().postDataJSON()
    await gate
    items = exchange(payload.message)
    await route.fulfill({ json: reply })
  })
  await page.goto('/#companion')
  await expect(page.getByRole('heading', { name: 'Je suis là, Alex.' })).toBeVisible()
  const input = page.getByRole('textbox', { name: 'Ce que tu souhaites partager' })
  await input.fill('  ')
  await expect(page.getByRole('button', { name: 'Envoyer' })).toBeDisabled()
  await input.fill('Une pause')
  await input.press('Shift+Enter')
  await input.press('x')
  expect(payload).toBeUndefined()
  await input.press('Enter')
  await expect(page.locator('.presence--thinking')).toBeVisible()
  await expect(input).toBeDisabled()
  await expect(page.locator('.transcript-entry')).toHaveCount(0)
  await page.clock.fastForward(21000)
  await expect(page.getByRole('status')).toContainText('Le compagnon local se prépare')
  expect(payload).toEqual({ user_id: 'ASTRO-001', message: 'Une pause\nx' })
  release()
  await expect(page.locator('.transcript-entry')).toHaveCount(2)
  await expect(page.locator('.transcript')).toContainText(reply.content)
  await expect(page.locator('.presence--attentive')).toBeVisible()
  await expect(input).toHaveValue('')
})

test('Ollama failure preserves text, retries once and never duplicates the transcript', async ({ page }) => {
  let calls = 0, items = []
  await page.route('**/api/chat/ASTRO-001', route => route.fulfill({ json: items }))
  await page.route('**/api/chat', route => {
    calls++
    if (calls === 1) return route.fulfill({ status: 503, json: { error: 'internal diagnostic' } })
    items = exchange(route.request().postDataJSON().message)
    return route.fulfill({ json: reply })
  })
  await page.goto('/#companion')
  const input = page.getByRole('textbox')
  await expect(input).toBeEnabled()
  await input.fill('Je suis fatigué.')
  await page.getByRole('button', { name: 'Envoyer' }).click()
  await expect(page.getByRole('alert')).toContainText('Je n’arrive pas à accéder à mon moteur de conversation')
  await expect(page.locator('body')).not.toContainText('503')
  await expect(input).toHaveValue('Je suis fatigué.')
  await expect(page.locator('.transcript-entry')).toHaveCount(0)
  await expect(page.locator('.presence--attentive')).toBeVisible()
  await page.getByRole('button', { name: 'Réessayer' }).click()
  await expect(page.locator('.transcript-entry')).toHaveCount(2)
  expect(calls).toBe(2)
})

test('a lost response is reconciled before retrying a persisted exchange', async ({ page }) => {
  let calls = 0, items = []
  await page.route('**/api/chat/ASTRO-001', route => route.fulfill({ json: items }))
  await page.route('**/api/chat', route => {
    calls++
    items = exchange(route.request().postDataJSON().message)
    return route.abort('failed')
  })
  await page.goto('/#companion')
  await expect(page.getByRole('textbox')).toBeEnabled()
  await page.getByRole('textbox').fill('Un peu de calme.')
  await page.getByRole('button', { name: 'Envoyer' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await page.getByRole('button', { name: 'Réessayer' }).click()
  await expect(page.locator('.transcript-entry')).toHaveCount(2)
  await expect(page.getByRole('textbox')).toHaveValue('')
  expect(calls).toBe(1)
})

test('a confirmed reply survives a history refresh error without a second POST', async ({ page }) => {
  let reads = 0, sends = 0, items = []
  await page.route('**/api/chat/ASTRO-001', route => {
    reads++
    // StrictMode may issue an aborted initial GET; use presence of the stored reply.
    if (items.length && reads < 100) { reads = 100; return route.fulfill({ status: 500 }) }
    return route.fulfill({ json: items })
  })
  await page.route('**/api/chat', route => {
    sends++; items = exchange(route.request().postDataJSON().message)
    return route.fulfill({ json: reply })
  })
  await page.goto('/#companion')
  await expect(page.getByRole('textbox')).toBeEnabled()
  await page.getByRole('textbox').fill('Bonjour.')
  await page.getByRole('button', { name: 'Envoyer' }).click()
  await expect(page.getByRole('alert')).toContainText('La réponse est arrivée')
  await expect(page.locator('.transcript')).toContainText(reply.content)
  await page.getByRole('button', { name: 'Actualiser la conversation' }).click()
  await expect(page.locator('.transcript-entry')).toHaveCount(2)
  await expect(page.getByRole('textbox')).toBeEnabled()
  expect(sends).toBe(1)
})

test('history errors stay human, without pretending the conversation is empty', async ({ page }) => {
  await page.route('**/api/chat/ASTRO-001', route => route.fulfill({ status: 500 }))
  await page.goto('/#companion')
  await expect(page.getByRole('alert')).toContainText('retrouver notre conversation')
  await expect(page.getByRole('textbox')).toBeDisabled()
  await expect(page.locator('.conversation-empty')).toHaveCount(0)
  await emptyHistory(page)
  await page.getByRole('button', { name: 'Réessayer' }).click()
  await expect(page.getByRole('textbox')).toBeEnabled()
})

test('reading older messages does not force a scroll, and tablet motion is reduced', async ({ page }) => {
  const items = Array.from({ length: 25 }, (_, index) => ({ ...reply, id: `history-${index}`, content: `Texte de test ${index}. Un moment de calme pour prendre le temps de parler.` }))
  let release
  const gate = new Promise(resolve => { release = resolve })
  await page.route('**/api/chat/ASTRO-001', route => route.fulfill({ json: items }))
  await page.route('**/api/chat', async route => { await gate; items.push(...exchange('Je suis là.')); await route.fulfill({ json: reply }) })
  await page.setViewportSize({ width: 768, height: 1024 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/#companion')
  await expect(page.getByRole('textbox')).toBeEnabled()
  await page.getByRole('textbox').fill('Je suis là.')
  await page.getByRole('button', { name: 'Envoyer' }).click()
  await expect(page.locator('.presence--thinking')).toBeVisible()
  expect(await page.locator('.presence-body').evaluate(el => getComputedStyle(el).animationName)).toBe('none')
  await page.locator('.transcript').evaluate(el => { el.scrollTop = 0; el.dispatchEvent(new Event('scroll')) })
  release()
  await expect(page.locator('.transcript-entry')).toHaveCount(27)
  expect(await page.locator('.transcript').evaluate(el => el.scrollTop)).toBe(0)
  await page.getByRole('button', { name: 'Revenir aux derniers échanges ↓' }).click()
  expect(await page.locator('.transcript').evaluate(el => el.scrollTop)).toBeGreaterThan(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
})

test('explicit real Ollama exchange persists and transitions attentive thinking attentive', async ({ page }) => {
  test.skip(process.env.PSYCHOSPACE_REAL_CHAT !== '1', 'Opt in: runs the local model and stores a real exchange.')
  test.setTimeout(420000)
  const before = await (await page.request.get('/api/chat/ASTRO-001')).json()
  await page.goto('/#companion')
  await expect(page.getByRole('textbox')).toBeEnabled()
  await expect(page.locator('.presence--attentive')).toBeVisible()
  await page.getByRole('textbox').fill('Ça va, je suis juste fatigué.')
  const response = page.waitForResponse(res => res.url().endsWith('/api/chat') && res.request().method() === 'POST', { timeout: 400000 })
  const start = Date.now()
  await page.getByRole('button', { name: 'Envoyer' }).click()
  await expect(page.locator('.presence--thinking')).toBeVisible()
  const result = await response
  const body = await result.json()
  console.log('REAL_CHAT_RESPONSE', result.status(), JSON.stringify(body), 'UI_SECONDS', ((Date.now() - start) / 1000).toFixed(2))
  expect(result.status()).toBe(200)
  await expect(page.locator('.presence--attentive')).toBeVisible()
  await expect(page.locator('.transcript-entry').last()).toContainText(body.content)
  const after = await (await page.request.get('/api/chat/ASTRO-001')).json()
  expect(after).toHaveLength(before.length + 2)
  expect(after.at(-2).content).toBe('Ça va, je suis juste fatigué.')
  expect(after.at(-1).content).toBe(body.content)
  await page.screenshot({ path: 'test-results/companion-real.png', fullPage: true })
  console.log('REAL_CHAT_PERSISTED', after.at(-2).id, after.at(-1).id)
})
