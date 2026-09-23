import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createVoiceService, selectLocalVoice } from '../src/services/voice.js'

const french = { name: 'Voix française quelconque', lang: 'fr-FR', localService: true }
function setup(voices = [french]) {
  const synth = new EventTarget()
  synth.getVoices = () => voices
  synth.cancel = () => { synth.cancels = (synth.cancels || 0) + 1 }
  synth.speak = utterance => { synth.current = utterance }
  const storage = new Map(), logs = []
  const service = createVoiceService({ speechSynthesis: synth, SpeechSynthesisUtterance: class { constructor(text) { this.text = text } }, localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) }, console: { info: message => logs.push(message) } })
  return { synth, service, logs }
}

test('French selection prefers local fr-FR then other French then local default; remote voices never used', () => {
  const english = { lang: 'en-US', localService: true, default: true }, canadian = { lang: 'fr-CA', localService: true }
  assert.equal(selectLocalVoice([english, canadian, french]), french)
  assert.equal(selectLocalVoice([english, canadian]), canadian)
  assert.equal(selectLocalVoice([english]), english)
  assert.equal(selectLocalVoice([{ ...french, localService: false }]), null)
})
test('speaking follows actual events, preserves exact visible text, ends and cancels stale callbacks', () => {
  const { service, synth } = setup()
  service.speak('Une réponse visible.', 'one')
  assert.equal(synth.current.text, 'Une réponse visible.')
  assert.equal(service.getSnapshot().speaking, false)
  synth.current.onstart()
  assert.equal(service.getSnapshot().speaking, true)
  const stale = synth.current.onend
  service.speak('La suivante.', 'two')
  synth.current.onstart(); stale()
  assert.equal(service.getSnapshot().activeId, 'two')
  synth.current.onend()
  assert.equal(service.getSnapshot().speaking, false)
  service.speak('Encore.', 'three'); service.stop()
  assert.equal(service.getSnapshot().activeId, null)
  assert.equal(service.getSnapshot().pending, false)
  assert.ok(synth.cancels >= 3)
})
test('fallback is logged; failures, unsupported API and preference are safe', () => {
  const { service, synth, logs } = setup([{ lang: 'en-US', localService: true, default: true }])
  service.setEnabled(true); assert.equal(service.getEnabled(), true)
  service.speak('Bonjour.', 'one'); assert.equal(logs.length, 1)
  synth.current.onerror({ error: 'not-allowed' })
  assert.equal(service.getSnapshot().speaking, false)
  assert.match(service.getSnapshot().error, /Écouter/)
  service.setEnabled(false); assert.equal(service.getEnabled(), false)
  const unsupported = createVoiceService({})
  unsupported.speak('Bonjour.', 'one')
  assert.match(unsupported.getSnapshot().error, /pas disponible/)
  const remote = setup([{ ...french, localService: false }])
  remote.service.speak('Bonjour.', 'one'); assert.equal(remote.synth.current, undefined)
})
test('voiceschanged refreshes late-arriving voices without speaking automatically', () => {
  const voices = [], { service, synth } = setup(voices)
  const unsubscribe = service.subscribe(() => {})
  assert.equal(service.getSnapshot().selectedVoice, null)
  voices.push(french); synth.dispatchEvent(new Event('voiceschanged'))
  assert.equal(service.getSnapshot().selectedVoice, french)
  assert.equal(synth.current, undefined)
  unsubscribe(); service.stop()
})
