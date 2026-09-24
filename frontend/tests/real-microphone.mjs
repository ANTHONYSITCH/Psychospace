// Interactive diagnostic: actual microphone, actual backend and native system voice.
// Run from frontend: node tests/real-microphone.mjs
// No audio or transcript is written by this diagnostic. Terminal output contains results.
import { chromium } from '@playwright/test'
const browser = await chromium.launch({ channel: 'msedge', headless: false })
const context = await browser.newContext()
const page = await context.newPage()
await page.addInitScript(() => {
  window.voiceEvidence = []
  const original = speechSynthesis.speak.bind(speechSynthesis)
  speechSynthesis.speak = utterance => {
    voiceEvidence.push({ event: 'requested', name: utterance.voice?.name, local: utterance.voice?.localService, lang: utterance.lang })
    for (const name of ['start', 'end', 'error']) utterance.addEventListener(name, event => voiceEvidence.push({ event: name, error: event.error }))
    original(utterance)
  }
})
const starts = new Map()
page.on('request', request => { if (request.method() === 'POST') starts.set(request, Date.now()) })
page.on('response', async response => {
  if (response.request().method() !== 'POST') return
  const path = new URL(response.url()).pathname
  if (!['/api/voice/transcribe', '/api/chat'].includes(path)) return
  console.log(JSON.stringify({ path, status: response.status(), elapsed_ms: Date.now() - starts.get(response.request()), result: await response.json() }))
})
await page.goto('http://127.0.0.1:5173/#companion')
await page.getByRole('checkbox', { name: 'Réponses vocales' }).check()
console.log('READY: click Parler, allow microphone, wait for Je t’écoute..., speak, stop, review, then click Envoyer.')
let previous = ''
const interval = setInterval(async () => {
  try {
    const events = JSON.stringify(await page.evaluate(() => voiceEvidence))
    if (events !== previous) { previous = events; console.log('NATIVE_VOICE', events) }
  } catch { clearInterval(interval) }
}, 1000)
await new Promise(resolve => browser.on('disconnected', resolve))
clearInterval(interval)
