// No network synthesis: never let the browser implicitly choose a remote voice.
export function selectLocalVoice(voices) {
  const local = voices.filter(voice => voice.localService === true)
  const language = voice => voice.lang.toLowerCase().replaceAll('_', '-')
  return local.find(voice => language(voice) === 'fr-fr')
    || local.find(voice => /^fr(?:-|$)/.test(language(voice)))
    || local.find(voice => voice.default) || local[0] || null
}

export function createVoiceService(environment) {
  const synth = environment?.speechSynthesis, Utterance = environment?.SpeechSynthesisUtterance
  const supported = Boolean(synth && Utterance)
  let snapshot = { supported, voices: [], selectedVoice: null, speaking: false, pending: false, activeId: null, error: '' }
  const listeners = new Set()
  let generation = 0, utterance = null, timer = null, warnedFallback = false
  function publish(change) { snapshot = { ...snapshot, ...change }; listeners.forEach(listener => listener(snapshot)) }
  function refresh() {
    let voices = []
    try { voices = supported ? synth.getVoices().filter(voice => voice.localService === true) : [] } catch { /* Leave text usable. */ }
    publish({ voices, selectedVoice: selectLocalVoice(voices) })
  }
  function stop() {
    generation++
    clearTimeout(timer); timer = null
    if (utterance) { utterance.onstart = null; utterance.onend = null; utterance.onerror = null; utterance = null }
    try { synth?.cancel() } catch { /* Cancellation must not break navigation. */ }
    publish({ speaking: false, pending: false, activeId: null, error: '' })
  }
  function speak(text, id) {
    stop(); refresh()
    if (!supported || !snapshot.selectedVoice) {
      publish({ error: 'La voix n’est pas disponible sur cet appareil.' }); return
    }
    if (typeof text !== 'string' || !text.trim()) return
    const voice = snapshot.selectedVoice
    if (!/^fr(?:-|$)/i.test(voice.lang.replaceAll('_', '-')) && !warnedFallback) {
      environment.console?.info('PsychoSpace : aucune voix française locale ; utilisation de la voix locale par défaut.')
      warnedFallback = true
    }
    const token = generation
    const finish = error => {
      if (token !== generation) return
      clearTimeout(timer); timer = null; utterance = null
      publish({ speaking: false, pending: false, activeId: null, error })
    }
    try {
      utterance = new Utterance(text)
      utterance.voice = voice; utterance.lang = voice.lang; utterance.rate = .95; utterance.pitch = 1; utterance.volume = 1
      utterance.onstart = () => {
        if (token !== generation) return
        clearTimeout(timer); timer = null; publish({ pending: false, speaking: true })
      }
      utterance.onend = () => finish('')
      utterance.onerror = () => finish('Je n’ai pas pu lire cette réponse. Tu peux réessayer avec « Écouter ».')
      publish({ activeId: id, pending: true, speaking: false, error: '' })
      timer = setTimeout(() => {
        if (token !== generation) return
        stop(); publish({ error: 'La lecture n’a pas démarré. Tu peux réessayer avec « Écouter ».' })
      }, 8000)
      synth.speak(utterance)
    } catch { finish('Je n’ai pas pu lire cette réponse. Le texte reste disponible.') }
  }
  return {
    getSnapshot: () => snapshot,
    subscribe(listener) {
      if (!listeners.size) synth?.addEventListener?.('voiceschanged', refresh)
      listeners.add(listener); refresh(); listener(snapshot)
      return () => { listeners.delete(listener); if (!listeners.size) synth?.removeEventListener?.('voiceschanged', refresh) }
    },
    speak, stop,
    getEnabled() { try { return environment?.localStorage?.getItem('voiceEnabled') === 'true' } catch { return false } },
    setEnabled(enabled) {
      try { environment?.localStorage?.setItem('voiceEnabled', String(enabled)) } catch { /* Session preference still works. */ }
      if (!enabled) stop()
    },
  }
}

export const voice = createVoiceService(typeof window === 'undefined' ? undefined : window)
