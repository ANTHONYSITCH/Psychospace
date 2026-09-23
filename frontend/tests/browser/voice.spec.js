import { test, expect } from '@playwright/test'

async function mockVoice(page, unavailable = false) {
  await page.addInitScript(unavailable => {
    if (unavailable) { Object.defineProperty(window, 'speechSynthesis', { value: undefined }); return }
    const synth = new EventTarget()
    window.voiceTest = { spoken: [], cancelCount: 0, current: null }
    synth.getVoices = () => [{ name: 'Français local de test', lang: 'fr-FR', localService: true, default: true }, { name: 'Voix distante interdite', lang: 'fr-FR', localService: false }]
    synth.cancel = () => { window.voiceTest.cancelCount++; window.voiceTest.current = null }
    synth.speak = utterance => { window.voiceTest.spoken.push(utterance.text); window.voiceTest.current = utterance; utterance.onstart?.() }
    Object.defineProperty(window, 'speechSynthesis', { value: synth })
    Object.defineProperty(window, 'SpeechSynthesisUtterance', { value: class { constructor(text) { this.text = text } } })
  }, unavailable)
}
async function mockChat(page) {
  let records = [{ id: 'old', role: 'assistant', content: 'Un ancien échange reste visible.' }], count = 0
  await page.route('**/api/chat/ASTRO-001', route => route.fulfill({ json: records }))
  await page.route('**/api/chat', async route => {
    const reply = { timestamp: `2080-04-16T18:00:0${++count}Z`, role: 'assistant', content: 'Tu peux prendre un moment pour souffler.' }
    records.push({ id: `user-${count}`, role: 'user', content: route.request().postDataJSON().message }, { ...reply, id: `answer-${count}` })
    await route.fulfill({ json: reply })
  })
}

test('voice preference, visible replies, speaking and end; no autoplay of history or remote requests', async ({ page }) => {
  await mockVoice(page); await mockChat(page)
  const requests = []
  page.on('request', request => requests.push(request.url()))
  await page.goto('/#companion')
  await expect(page.getByRole('textbox')).toBeEnabled()
  expect(await page.evaluate(() => voiceTest.spoken)).toEqual([])
  await page.getByRole('checkbox', { name: 'Réponses vocales' }).check()
  expect(await page.evaluate(() => localStorage.getItem('voiceEnabled'))).toBe('true')
  expect(await page.evaluate(() => voiceTest.spoken)).toEqual([])
  await page.getByRole('textbox').fill('Bonjour.')
  await page.getByRole('button', { name: 'Envoyer', exact: true }).click()
  await expect(page.locator('.presence--speaking')).toBeVisible()
  const visible = await page.locator('.transcript-entry--assistant p').last().textContent()
  expect(await page.evaluate(() => voiceTest.spoken)).toEqual([visible])
  await page.evaluate(() => voiceTest.current.onend())
  await expect(page.locator('.presence--attentive')).toBeVisible()
  await page.getByRole('button', { name: 'Écouter cette réponse' }).last().focus()
  await page.keyboard.press('Enter')
  await expect(page.locator('.presence--speaking')).toBeVisible()
  await page.getByRole('button', { name: 'Arrêter', exact: true }).click()
  await expect(page.locator('.presence--attentive')).toBeVisible()
  await page.getByRole('textbox').fill('Et maintenant ?')
  await page.getByRole('button', { name: 'Envoyer', exact: true }).click()
  await expect(page.locator('.presence--speaking')).toBeVisible()
  expect(await page.evaluate(() => voiceTest.spoken.length)).toBe(3)
  await page.getByRole('button', { name: 'Arrêter', exact: true }).click()
  await page.reload()
  await expect(page.getByRole('checkbox', { name: 'Réponses vocales' })).toBeChecked()
  expect(await page.evaluate(() => voiceTest.spoken)).toEqual([])
  expect(requests.every(url => new URL(url).hostname === '127.0.0.1')).toBeTruthy()
})

test('new message, navigation and disabling cancel speech; reduced motion and speech errors preserve text', async ({ page }) => {
  await mockVoice(page); await mockChat(page)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/#companion')
  await page.getByRole('checkbox', { name: 'Réponses vocales' }).check()
  await page.getByRole('button', { name: 'Écouter cette réponse' }).click()
  await expect(page.locator('.presence--speaking')).toBeVisible()
  expect(await page.locator('.presence-body').evaluate(el => getComputedStyle(el).animationName)).toBe('none')
  let release
  const pending = new Promise(resolve => { release = resolve })
  await page.route('**/api/chat', async route => { await pending; await route.fulfill({ status: 503 }) })
  const before = await page.evaluate(() => voiceTest.cancelCount)
  await page.getByRole('textbox').fill('Un autre message.')
  await page.getByRole('button', { name: 'Envoyer', exact: true }).click()
  await expect(page.locator('.presence--thinking')).toBeVisible()
  expect(await page.evaluate(() => voiceTest.cancelCount)).toBeGreaterThan(before)
  release()
  await expect(page.getByRole('textbox')).toBeEnabled()
  await page.getByRole('button', { name: 'Écouter cette réponse' }).click()
  await page.evaluate(() => voiceTest.current.onerror({ error: 'not-allowed' }))
  await expect(page.getByText('Je n’ai pas pu lire cette réponse. Tu peux réessayer avec « Écouter ».')).toBeVisible()
  await expect(page.locator('.presence--attentive')).toBeVisible()
  await page.getByRole('button', { name: 'Écouter cette réponse' }).click()
  await page.getByRole('checkbox', { name: 'Réponses vocales' }).uncheck()
  await expect(page.locator('.presence--attentive')).toBeVisible()
  await expect(page.locator('.transcript')).toContainText('Un ancien échange reste visible.')
  await page.getByRole('checkbox', { name: 'Réponses vocales' }).check()
  await page.getByRole('button', { name: 'Écouter cette réponse' }).click()
  const cancels = await page.evaluate(() => voiceTest.cancelCount)
  await page.getByRole('link', { name: 'Mémoire', exact: true }).click()
  expect(await page.evaluate(() => voiceTest.cancelCount)).toBeGreaterThan(cancels)
  expect(await page.evaluate(() => voiceTest.current)).toBeNull()
})

test('missing synthesis never blocks text chat', async ({ page }) => {
  await mockVoice(page, true); await mockChat(page)
  await page.goto('/#companion')
  await expect(page.getByText('La voix n’est pas disponible sur cet appareil.')).toBeVisible()
  await page.getByRole('textbox').fill('Bonjour.')
  await page.getByRole('button', { name: 'Envoyer', exact: true }).click()
  await expect(page.locator('.transcript-entry--assistant').last()).toContainText('Tu peux prendre un moment pour souffler.')
})

test('real Ollama reply and Windows local voice follow the four presence states', async ({ page }) => {
  test.skip(process.env.PSYCHOSPACE_REAL_VOICE !== '1', 'Explicit real chat and system audio only')
  test.setTimeout(540000)
  // Observe native events only; no synthesis or chat mock in this test.
  await page.addInitScript(() => {
    window.realVoiceEvents = []
    const original = speechSynthesis.speak.bind(speechSynthesis)
    speechSynthesis.speak = utterance => {
      realVoiceEvents.push({ event: 'requested', name: utterance.voice?.name, lang: utterance.voice?.lang, local: utterance.voice?.localService, text: utterance.text })
      for (const name of ['start', 'end', 'error']) utterance.addEventListener(name, event => realVoiceEvents.push({ event: name, error: event.error }))
      original(utterance)
    }
  })
  await page.goto('/#companion')
  await expect(page.getByRole('textbox')).toBeEnabled()
  await expect(page.locator('.presence--attentive')).toBeVisible()
  await page.getByRole('checkbox', { name: 'Réponses vocales' }).check()
  await page.getByRole('textbox').fill('Ça va, je suis juste fatigué.')
  const response = page.waitForResponse(res => res.url().endsWith('/api/chat') && res.request().method() === 'POST', { timeout: 400000 })
  await page.getByRole('button', { name: 'Envoyer', exact: true }).click()
  await expect(page.locator('.presence--thinking')).toBeVisible()
  const result = await response
  expect(result.status()).toBe(200)
  const reply = await result.json()
  await expect(page.locator('.transcript-entry--assistant p').last()).toHaveText(reply.content)
  // Native autoplay may be denied after a slow model response: a manual click is allowed.
  try { await expect(page.locator('.presence--speaking')).toBeVisible({ timeout: 10000 }) }
  catch { await page.getByRole('button', { name: 'Écouter cette réponse' }).last().click(); await expect(page.locator('.presence--speaking')).toBeVisible({ timeout: 10000 }) }
  await page.screenshot({ path: 'test-results/voice-real-speaking.png', fullPage: true })
  await expect(page.locator('.presence--attentive')).toBeVisible({ timeout: 180000 })
  const events = await page.evaluate(() => realVoiceEvents)
  console.log('REAL_WINDOWS_VOICE', JSON.stringify(events))
  expect(events.some(event => event.event === 'start')).toBeTruthy()
  expect(events.some(event => event.event === 'end')).toBeTruthy()
  const spoken = events.filter(event => event.event === 'requested')
  expect(spoken.every(event => event.local === true && event.lang === 'fr-FR' && event.text === reply.content)).toBeTruthy()
  const persisted = await (await page.request.get('/api/chat/ASTRO-001')).json()
  expect(persisted.some(item => item.timestamp === reply.timestamp && item.role === 'assistant' && item.content === reply.content)).toBeTruthy()
})
