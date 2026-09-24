import { test, expect } from '@playwright/test'

async function mock(page, status = 'available') {
  await page.addInitScript(status => {
    window.recTest = { status, failInstall: false, calls: [], instance: null }
    class Recognition {
      processLocally = false
      static async available(options) { recTest.calls.push(['available', options]); return recTest.status }
      static async install(options) { recTest.calls.push(['install', options]); if (recTest.failInstall) return false; recTest.status = 'available'; return true }
      start() { recTest.instance = this; recTest.calls.push(['start', this.processLocally, this.lang]); this.onstart() }
      abort() { recTest.calls.push(['abort']); recTest.instance = null }
    }
    Object.defineProperty(window, 'SpeechRecognition', { value: Recognition })
    window.recResult = (text, final) => recTest.instance.onresult({ results: [Object.assign([{ transcript: text }], { isFinal: final })] })
    const synth = new EventTarget()
    synth.getVoices = () => [{ name: 'Voix locale de test', lang: 'fr-FR', localService: true }]
    synth.cancel = () => { recTest.calls.push(['speech-stop']) }
    synth.speak = utterance => { recTest.utterance = utterance; utterance.onstart() }
    Object.defineProperty(window, 'speechSynthesis', { value: synth })
    Object.defineProperty(window, 'SpeechSynthesisUtterance', { value: class { constructor(text) { this.text = text } } })
  }, status)
  let items = [{ id: 'old', role: 'assistant', content: 'Un moment pour toi.' }]
  await page.route('**/api/chat/ASTRO-001', route => route.fulfill({ json: items }))
  await page.route('**/api/chat', async route => {
    const reply = { role: 'assistant', content: 'Je suis là.', timestamp: '2080-04-16T19:00:00Z' }
    items.push({ id: 'user', role: 'user', content: route.request().postDataJSON().message }, { ...reply, id: 'reply' })
    await route.fulfill({ json: reply })
  })
}
test('local interim then final remains editable until explicit send; speech and recognition never overlap', async ({ page }) => {
  await mock(page)
  const requests = [], posts = []
  page.on('request', request => { requests.push(request.url()); if (request.method() === 'POST') posts.push(request.postDataJSON()) })
  await page.goto('/#companion')
  await page.getByRole('checkbox', { name: 'Réponses vocales' }).check()
  await page.getByRole('button', { name: 'Écouter cette réponse' }).click()
  await expect(page.locator('.presence--speaking')).toBeVisible()
  await page.getByRole('button', { name: 'Parler à PsychoSpace' }).focus(); await page.keyboard.press('Enter')
  await expect(page.locator('.presence--listening')).toBeVisible()
  await expect(page.locator('.presence--speaking')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Écouter cette réponse' })).toBeDisabled()
  await page.evaluate(() => recResult('Ça va, je suis juste', false))
  await expect(page.locator('.microphone-interim')).toHaveText('Ça va, je suis juste')
  expect(posts).toEqual([])
  await page.evaluate(() => recResult('Ça va, je suis juste fatigué.', true))
  await expect(page.getByRole('textbox')).toHaveValue('Ça va, je suis juste fatigué.')
  await expect(page.locator('.presence--attentive')).toBeVisible()
  expect(posts).toEqual([])
  let release
  const pending = new Promise(resolve => { release = resolve })
  await page.route('**/api/chat', async route => { await pending; await route.fallback() })
  await page.getByRole('textbox').fill('Ça va, je suis un peu fatigué.')
  await page.getByRole('button', { name: 'Envoyer', exact: true }).click()
  await expect(page.locator('.presence--thinking')).toBeVisible()
  release()
  await expect(page.locator('.presence--speaking')).toBeVisible()
  expect(posts).toEqual([{ user_id: 'ASTRO-001', message: 'Ça va, je suis un peu fatigué.' }])
  await page.evaluate(() => recTest.utterance.onend())
  await expect(page.locator('.presence--attentive')).toBeVisible()
  const calls = await page.evaluate(() => recTest.calls)
  const start = calls.findIndex(call => call[0] === 'start')
  expect(calls[start]).toEqual(['start', true, 'fr-FR'])
  expect(calls.slice(0, start).some(call => call[0] === 'speech-stop')).toBeTruthy()
  expect(requests.every(url => new URL(url).hostname === '127.0.0.1')).toBeTruthy()
})
test('stop preserves draft, permission refusal preserves typing, navigation aborts and reduced motion holds', async ({ page }) => {
  await mock(page); await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/#companion')
  await page.getByRole('textbox').fill('Mon brouillon.')
  await page.getByRole('button', { name: 'Parler à PsychoSpace' }).click()
  expect(await page.locator('.presence-body').evaluate(el => getComputedStyle(el).animationName)).toBe('none')
  await page.evaluate(() => recResult('Une suite', false))
  await page.getByRole('button', { name: 'Arrêter le microphone' }).click()
  await expect(page.getByRole('textbox')).toHaveValue('Mon brouillon. Une suite')
  await page.getByRole('button', { name: 'Parler à PsychoSpace' }).click()
  await page.evaluate(() => recTest.instance.onerror({ error: 'not-allowed' }))
  await expect(page.getByText('Le microphone n’est pas autorisé. Tu peux continuer à m’écrire.')).toBeVisible()
  await expect(page.getByRole('textbox')).toBeEnabled()
  await page.getByRole('button', { name: 'Parler à PsychoSpace' }).click()
  await page.getByRole('link', { name: 'Mémoire', exact: true }).click()
  expect(await page.evaluate(() => recTest.instance)).toBeNull()
})
test('local installation is explicit, failure is visible and success never starts microphone', async ({ page }) => {
  await mock(page, 'downloadable'); await page.goto('/#companion')
  await expect(page.getByRole('button', { name: 'Parler à PsychoSpace' })).toBeDisabled()
  await page.evaluate(() => { recTest.failInstall = true })
  await page.getByRole('button', { name: 'Installer la reconnaissance vocale française' }).click()
  await expect(page.getByText('Je n’ai pas pu installer la reconnaissance vocale française. Tu peux continuer à m’écrire.')).toBeVisible()
  await page.evaluate(() => { recTest.failInstall = false })
  await page.getByRole('button', { name: 'Installer la reconnaissance vocale française' }).click()
  await expect(page.getByRole('button', { name: 'Parler à PsychoSpace' })).toBeEnabled()
  expect(await page.evaluate(() => recTest.calls.some(call => call[0] === 'start'))).toBe(false)
  await page.getByText('Ce que PsychoSpace utilise pour te répondre').click()
  await expect(page.getByText('Voix traitée sur cet appareil')).toBeVisible()
})
test('unavailable local recognition leaves keyboard enabled with no privacy claim', async ({ page }) => {
  await mock(page, 'unavailable'); await page.goto('/#companion')
  await expect(page.getByRole('button', { name: 'Parler à PsychoSpace' })).toBeDisabled()
  await expect(page.getByText(/La reconnaissance vocale locale n’est pas disponible/)).toBeVisible()
  await expect(page.getByRole('textbox')).toBeEnabled()
  await expect(page.getByText('Voix traitée sur cet appareil')).toHaveCount(0)
})
test('real Windows Edge capability, with visible browser and no recognition fallback', async ({ playwright }) => {
  test.skip(process.env.PSYCHOSPACE_REAL_MIC !== '1', 'Explicit real browser capability check')
  const browser = await playwright.chromium.launch({ channel: 'msedge', headless: false })
  try {
    const page = await browser.newPage()
    await page.goto('http://127.0.0.1:5173/#companion')
    const capability = await page.evaluate(async () => {
      const R = window.SpeechRecognition
      return { browser: navigator.userAgent, processLocally: Boolean(R && 'processLocally' in new R()), status: typeof R?.available === 'function' ? await R.available({ langs: ['fr-FR'], processLocally: true }) : 'API absente' }
    })
    console.log('REAL_LOCAL_RECOGNITION', JSON.stringify(capability))
    if (capability.status === 'available') await expect(page.getByRole('button', { name: 'Parler à PsychoSpace' })).toBeEnabled()
    else await expect(page.getByRole('button', { name: 'Parler à PsychoSpace' })).toBeDisabled()
    await expect(page.getByRole('textbox')).toBeEnabled()
    await page.screenshot({ path: 'test-results/recognition-real-windows.png', fullPage: true })
  } finally { await browser.close() }
})
