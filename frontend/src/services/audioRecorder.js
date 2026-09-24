export const localVoiceUnavailable = "La transcription vocale locale n'est pas disponible pour le moment. Tu peux continuer à m'écrire."
const formats = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg', 'audio/mp4', 'audio/wav', 'audio/mpeg']

export function createAudioRecorder(environment, transcribeAudio) {
  const Recorder = environment?.MediaRecorder
  const supported = Boolean(Recorder && environment?.navigator?.mediaDevices?.getUserMedia)
  let snapshot = { supported, starting: false, listening: false, transcribing: false, error: '' }
  let generation = 0, recorder = null, stream = null, timer = null, controller = null
  const listeners = new Set()
  const publish = change => { snapshot = { ...snapshot, ...change }; listeners.forEach(fn => fn(snapshot)) }
  const release = () => { clearTimeout(timer); timer = null; stream?.getTracks().forEach(track => track.stop()); stream = null }
  function abort() {
    generation++
    controller?.abort(); controller = null
    if (recorder) {
      recorder.onstart = recorder.ondataavailable = recorder.onstop = recorder.onerror = null
      try { if (recorder.state !== 'inactive') recorder.stop() } catch { /* Release tracks even if the recorder already failed. */ }
    }
    recorder = null; release()
    publish({ starting: false, listening: false, transcribing: false })
  }
  function stop() {
    if (snapshot.starting) { abort(); return }
    try { if (recorder && recorder.state !== 'inactive') recorder.stop() }
    catch { abort(); publish({ error: localVoiceUnavailable }) }
    finally { release() }
  }
  async function start(onText) {
    if (snapshot.starting || snapshot.listening || snapshot.transcribing) return
    if (!supported) { publish({ error: localVoiceUnavailable }); return }
    const token = ++generation
    publish({ starting: true, error: '' })
    try {
      const mimeType = formats.find(mime => Recorder.isTypeSupported(mime))
      if (!mimeType) throw new Error('No supported audio format')
      const acquired = await environment.navigator.mediaDevices.getUserMedia({ audio: true })
      if (token !== generation) { acquired.getTracks().forEach(track => track.stop()); return }
      stream = acquired
      recorder = new Recorder(stream, { mimeType })
      const chunks = []
      let size = 0
      recorder.onstart = () => {
        if (token !== generation) return
        publish({ starting: false, listening: true })
        timer = setTimeout(stop, 30000)
      }
      recorder.ondataavailable = event => {
        if (token !== generation || !event.data.size) return
        size += event.data.size
        if (size > 10485760) { abort(); publish({ error: "L'audio est trop volumineux. Tu peux recommencer ou m'écrire." }); return }
        chunks.push(event.data)
      }
      recorder.onerror = () => { abort(); publish({ error: localVoiceUnavailable }) }
      recorder.onstop = async () => {
        if (token !== generation) return
        const type = recorder.mimeType || chunks[0]?.type || mimeType
        recorder = null; release()
        publish({ starting: false, listening: false, transcribing: true })
        controller = new AbortController()
        try {
          const result = await transcribeAudio(new Blob(chunks, { type }), controller.signal)
          if (token !== generation) return
          if (result.text.trim()) onText(result.text)
          else publish({ error: "Je n'ai pas entendu de parole. Tu peux réessayer ou m'écrire." })
        } catch { if (token === generation) publish({ error: localVoiceUnavailable }) }
        finally { if (token === generation) { controller = null; publish({ transcribing: false }) } }
      }
      recorder.start(250)
    } catch (error) {
      if (token !== generation) return
      abort()
      publish({ error: error.name === 'NotAllowedError' ? "Le microphone n'est pas autorisé. Tu peux continuer à m'écrire." : localVoiceUnavailable })
    }
  }
  return { getSnapshot: () => snapshot, start, stop, abort,
    subscribe(fn) { listeners.add(fn); fn(snapshot); return () => listeners.delete(fn) } }
}
