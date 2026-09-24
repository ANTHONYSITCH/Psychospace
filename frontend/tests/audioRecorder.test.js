import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createAudioRecorder } from '../src/services/audioRecorder.js'

function setup({ supported = ['audio/ogg;codecs=opus'], permission } = {}) {
  const state = { calls: [], stopped: 0, uploads: [] }
  const stream = { getTracks: () => [{ stop() { state.stopped++ } }] }
  class Recorder {
    static isTypeSupported(mime) { state.calls.push(mime); return supported.includes(mime) }
    constructor(acquired, options) { assert.equal(acquired, stream); this.mimeType = options.mimeType; state.recorder = this; this.state = 'inactive' }
    start() { this.state = 'recording' }
    stop() { this.state = 'inactive'; this.ondataavailable?.({ data: new Blob(['voice'], { type: this.mimeType }) }); this.pending = this.onstop?.() }
  }
  const service = createAudioRecorder({ MediaRecorder: Recorder, navigator: { mediaDevices: {
    async getUserMedia(options) { assert.deepEqual(options, { audio: true }); if (permission) await permission; return stream },
  } } }, async (blob, signal) => {
    state.uploads.push({ blob, signal })
    return state.result ? await state.result : { text: 'Bonjour Alex.' }
  })
  return { state, service }
}

test('unsupported recorder leaves typing fallback', async () => {
  const service = createAudioRecorder({}, () => assert.fail('No upload'))
  assert.equal(service.getSnapshot().supported, false)
  await service.start()
  assert.match(service.getSnapshot().error, /continuer à m'écrire/)
})

test('MIME negotiation, actual start event, blob, transcription and track release', async () => {
  const { service, state } = setup()
  const texts = [], states = []
  service.subscribe(value => states.push(value))
  await service.start(text => texts.push(text))
  assert.equal(service.getSnapshot().starting, true)
  assert.equal(service.getSnapshot().listening, false)
  assert.equal(state.recorder.mimeType, 'audio/ogg;codecs=opus')
  state.recorder.onstart()
  assert.equal(service.getSnapshot().listening, true)
  service.stop(); await state.recorder.pending
  assert.equal(state.stopped, 1)
  assert.equal(state.uploads[0].blob.type, 'audio/ogg;codecs=opus')
  assert.equal(await state.uploads[0].blob.text(), 'voice')
  assert.deepEqual(texts, ['Bonjour Alex.'])
  assert.ok(states.some(value => value.transcribing && !value.listening))
  assert.equal(service.getSnapshot().transcribing, false)
})

test('microphone permission refusal', async () => {
  const { service, state } = setup({ permission: Promise.reject(Object.assign(new Error(), { name: 'NotAllowedError' })) })
  await service.start()
  assert.match(service.getSnapshot().error, /microphone n'est pas autorisé/)
  assert.equal(state.uploads.length, 0)
})

test('no supported MIME never acquires microphone', async () => {
  const { service, state } = setup({ supported: [] })
  await service.start()
  assert.equal(state.recorder, undefined)
  assert.match(service.getSnapshot().error, /pas disponible/)
})

test('navigation while permission pending releases late tracks', async () => {
  let release
  const { service, state } = setup({ permission: new Promise(resolve => { release = resolve }) })
  const pending = service.start(() => assert.fail('stale text'))
  service.abort(); release(); await pending
  assert.equal(state.stopped, 1)
  assert.equal(state.recorder, undefined)
})

test('navigation during recording stops recorder without uploading', async () => {
  const { service, state } = setup()
  await service.start(() => assert.fail('stale text')); state.recorder.onstart()
  service.abort()
  assert.equal(state.recorder.state, 'inactive')
  assert.equal(state.stopped, 1)
  assert.equal(state.uploads.length, 0)
})

test('navigation cancels transcription and ignores late response', async () => {
  const { service, state } = setup()
  let release
  state.result = new Promise(resolve => { release = resolve })
  await service.start(() => assert.fail('stale text')); state.recorder.onstart(); service.stop()
  service.abort()
  assert.equal(state.uploads[0].signal.aborted, true)
  release({ text: 'late' }); await state.recorder.pending
  assert.equal(service.getSnapshot().transcribing, false)
})

test('automatic stop after 30 seconds', async context => {
  context.mock.timers.enable({ apis: ['setTimeout'] })
  const { service, state } = setup()
  await service.start(() => {}); state.recorder.onstart()
  context.mock.timers.tick(29999)
  assert.equal(state.stopped, 0)
  context.mock.timers.tick(1); await state.recorder.pending
  assert.equal(state.stopped, 1)
  assert.equal(state.uploads.length, 1)
})

test('empty transcription and unavailable server leave recoverable fallback', async () => {
  for (const result of [{ text: '' }, null]) {
    const { service, state } = setup()
    state.result = result ? Promise.resolve(result) : { then(resolve, reject) { reject(new Error('offline')) } }
    await service.start(() => assert.fail('No invented text')); state.recorder.onstart(); service.stop()
    await state.recorder.pending
    assert.match(service.getSnapshot().error, /écrire/)
    assert.equal(service.getSnapshot().transcribing, false)
    assert.equal(state.stopped, 1)
  }
})

test('size overflow aborts and releases microphone without upload', async () => {
  const { service, state } = setup()
  await service.start(() => assert.fail('No text')); state.recorder.onstart()
  state.recorder.ondataavailable({ data: new Blob([new Uint8Array(10485761)]) })
  assert.equal(state.stopped, 1)
  assert.equal(state.uploads.length, 0)
  assert.match(service.getSnapshot().error, /volumineux/)
})
