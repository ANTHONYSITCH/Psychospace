import { test, expect } from '@playwright/test'

async function setup(page, { denied = false, unavailable = false } = {}) {
  await page.addInitScript(({ denied }) => {
    Object.defineProperty(window, 'SpeechRecognition', { value: undefined })
    window.audioTest = { stops: 0, calls: [], recorder: null }
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', { value: async () => {
      if (denied) throw Object.assign(new Error(), { name: 'NotAllowedError' })
      return { getTracks: () => [{ stop() { audioTest.stops++ } }] }
    } })
    class Recorder {
      static isTypeSupported(type) { return type === 'audio/webm;codecs=opus' }
      constructor(stream, options) { this.mimeType = options.mimeType; this.state = 'inactive'; audioTest.recorder = this }
      start() { this.state = 'recording'; audioTest.calls.push('record-start') }
      stop() { this.state = 'inactive'; this.ondataavailable?.({ data: new Blob(['audio'], { type: this.mimeType }) }); this.onstop?.() }
    }
    Object.defineProperty(window, 'MediaRecorder', { value: Recorder })
    const synth = new EventTarget()
    synth.getVoices = () => [{ name: 'Voix locale test', lang: 'fr-FR', localService: true }]
    synth.cancel = () => audioTest.calls.push('speech-stop')
    synth.speak = utterance => utterance.onstart()
    Object.defineProperty(window, 'speechSynthesis', { value: synth })
    Object.defineProperty(window, 'SpeechSynthesisUtterance', { value: class {} })
  }, { denied })
  await page.route('**/api/chat/ASTRO-001', route => route.fulfill({ json: [{ id: 'old', role: 'assistant', content: 'Bonjour.' }] }))
  await page.route('**/api/profile/ASTRO-001', route => route.fulfill({ json: { first_name: 'Alex' } }))
  let release
  const gate = new Promise(resolve => { release = resolve })
  const uploads = [], chats = []
  await page.route('**/api/voice/transcribe', async route => {
    uploads.push({ type: route.request().headers()['content-type'], body: route.request().postData() })
    await gate
    await route.fulfill({ status: unavailable ? 503 : 200, json: unavailable ? {} : { text: 'Ça va, je suis juste fatigué.', language: 'fr', processing_ms: 42 } })
  })
  await page.route('**/api/chat', route => { chats.push(route.request().postDataJSON()); return route.fulfill({ json: { role: 'assistant', content: 'Je suis là.', timestamp: 'test' } }) })
  await page.goto('/#companion')
  return { release, uploads, chats }
}

test('Whisper flow waits for actual start, transcribes locally and requires corrected explicit send', async ({ page }) => {
  const requests = []
  page.on('request', request => requests.push(request.url()))
  const { release, uploads, chats } = await setup(page)
  await page.getByRole('checkbox', { name: 'Réponses vocales' }).check()
  await page.getByRole('button', { name: 'Écouter cette réponse' }).click()
  await expect(page.locator('.presence--speaking')).toBeVisible()
  await page.getByRole('button', { name: 'Parler à PsychoSpace' }).click()
  await expect(page.locator('.presence--listening')).toHaveCount(0)
  await expect(page.locator('.conversation-status')).toHaveText('Je suis là.')
  await page.evaluate(() => audioTest.recorder.onstart())
  await expect(page.locator('.presence--listening')).toBeVisible()
  await expect(page.locator('.conversation-status')).toHaveText('Je t’écoute...')
  const calls = await page.evaluate(() => audioTest.calls)
  expect(calls.indexOf('speech-stop')).toBeLessThan(calls.indexOf('record-start'))
  await page.getByRole('button', { name: 'Arrêter le microphone' }).click()
  await expect(page.locator('.presence--transcribing')).toBeVisible()
  await expect(page.locator('.conversation-status')).toHaveText('Je transforme ta voix en texte...')
  expect(await page.evaluate(() => audioTest.stops)).toBe(1)
  await expect.poll(() => uploads.length).toBe(1)
  expect(uploads[0]).toEqual({ type: 'audio/webm;codecs=opus', body: 'audio' })
  release()
  await expect(page.getByRole('textbox')).toHaveValue('Ça va, je suis juste fatigué.')
  await expect(page.locator('.presence--attentive')).toBeVisible()
  expect(chats).toEqual([])
  await expect(page.getByText(/Voix transcrite sur cet appareil/)).toBeVisible()
  await page.getByRole('textbox').fill('Je suis un peu fatigué.')
  await page.getByRole('button', { name: 'Envoyer', exact: true }).click()
  await expect.poll(() => chats.length).toBe(1)
  expect(chats[0].message).toBe('Je suis un peu fatigué.')
  expect(requests.every(url => new URL(url).hostname === '127.0.0.1')).toBe(true)
})

test('Whisper unavailable preserves draft and typing', async ({ page }) => {
  const { release, chats } = await setup(page, { unavailable: true })
  await page.getByRole('textbox').fill('Mon brouillon')
  await page.getByRole('button', { name: 'Parler à PsychoSpace' }).click()
  await page.evaluate(() => audioTest.recorder.onstart())
  await page.getByRole('button', { name: 'Arrêter le microphone' }).click(); release()
  await expect(page.getByText(/La transcription vocale locale n'est pas disponible/)).toBeVisible()
  await expect(page.getByRole('textbox')).toHaveValue('Mon brouillon')
  await expect(page.getByRole('textbox')).toBeEnabled()
  expect(chats).toEqual([])
})

test('microphone denied leaves keyboard available', async ({ page }) => {
  await setup(page, { denied: true })
  await page.getByRole('button', { name: 'Parler à PsychoSpace' }).click()
  await expect(page.getByText(/Le microphone n'est pas autorisé/)).toBeVisible()
  await expect(page.getByRole('textbox')).toBeEnabled()
})

test('leaving Companion releases microphone and never transcribes', async ({ page }) => {
  const { uploads } = await setup(page)
  await page.getByRole('button', { name: 'Parler à PsychoSpace' }).click()
  await page.evaluate(() => audioTest.recorder.onstart())
  await page.getByRole('link', { name: 'Mémoire', exact: true }).click()
  expect(await page.evaluate(() => audioTest.stops)).toBe(1)
  expect(uploads).toEqual([])
})
