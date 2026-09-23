import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createRecognitionService } from '../src/services/speechRecognition.js'

function setup(status = 'available') {
  const calls = [], instances = []
  class Recognition {
    processLocally = false
    constructor() { instances.push(this) }
    static async available(options) { calls.push(['available', options]); return status }
    static async install(options) { calls.push(['install', options]); status = 'available'; return true }
    start() { calls.push(['start', this.processLocally, this.lang]); this.onstart() }
    abort() { calls.push(['abort']) }
  }
  return { service: createRecognitionService({ SpeechRecognition: Recognition }), Recognition, calls, instances, setStatus(value) { status = value } }
}
function result(text, isFinal) { return { results: [Object.assign([{ transcript: text }], { isFinal })] } }
test('available local recognition uses French, interim and final, never sends anything', async () => {
  const { service, calls, instances } = setup(), finals = []
  await service.start(text => finals.push(text))
  assert.ok(calls.some(call => call[0] === 'start' && call[1] === true && call[2] === 'fr-FR'))
  assert.equal(service.getSnapshot().listening, true)
  instances.at(-1).onresult(result('Ça va', false))
  assert.equal(service.getSnapshot().interim, 'Ça va')
  assert.deepEqual(finals, [])
  instances.at(-1).onresult(result('Ça va, je suis juste fatigué.', true))
  assert.deepEqual(finals, ['Ça va, je suis juste fatigué.'])
  assert.equal(service.getSnapshot().listening, false)
})
test('missing API, absent local property and unavailable pack fail closed', async () => {
  const missing = createRecognitionService({ webkitSpeechRecognition: class {} })
  assert.equal(await missing.check(), 'unavailable')
  const legacy = createRecognitionService({ SpeechRecognition: class { static available() { throw Error('must not call') } } })
  assert.equal(legacy.getSnapshot().supported, false)
  const { service, calls } = setup('unavailable')
  await service.start(() => {})
  assert.equal(calls.some(call => call[0] === 'start'), false)
})
test('installation requires explicit call and rechecks local availability', async () => {
  const { service, calls } = setup('downloadable')
  await service.check(); assert.equal(calls.some(call => call[0] === 'install'), false)
  await service.install()
  assert.equal(service.getSnapshot().availability, 'available')
  assert.ok(calls.filter(call => call[0] === 'available' || call[0] === 'install').every(call => call[1].processLocally === true && call[1].langs[0] === 'fr-FR'))
  assert.equal(calls.some(call => call[0] === 'start'), false)
})
test('failed installation, downloading and denied microphone preserve keyboard fallback', async () => {
  const { service, Recognition, setStatus, instances } = setup('downloadable')
  Recognition.install = async () => false
  await service.check(); await service.install()
  assert.match(service.getSnapshot().error, /installer/)
  setStatus('downloading'); await service.check(); assert.equal(service.getSnapshot().availability, 'downloading')
  setStatus('available'); await service.start(() => {})
  instances.at(-1).onerror({ error: 'not-allowed' })
  assert.equal(service.getSnapshot().listening, false)
  assert.match(service.getSnapshot().error, /microphone n’est pas autorisé/)
})
test('manual stop retains partial text; leaving cancels pending start and ignores old results', async () => {
  const { service, Recognition, instances } = setup(), finals = []
  await service.start(text => finals.push(text))
  const old = instances.at(-1).onresult
  old(result('Une phrase', false)); service.stop(); old(result('Une autre', true))
  assert.deepEqual(finals, ['Une phrase'])
  let release
  Recognition.available = () => new Promise(resolve => { release = resolve })
  const pending = service.start(text => finals.push(text))
  service.abort(); release('available'); await pending
  assert.equal(service.getSnapshot().listening, false)
  assert.deepEqual(finals, ['Une phrase'])
})
