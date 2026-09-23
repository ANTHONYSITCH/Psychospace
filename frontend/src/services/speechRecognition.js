const options = { langs: ['fr-FR'], processLocally: true }
export const unavailableMessage = 'La reconnaissance vocale locale n’est pas disponible sur ce navigateur. Tu peux continuer à utiliser le clavier.'

export function createRecognitionService(environment) {
  const Recognition = environment?.SpeechRecognition
  let supported = false
  try { supported = Boolean(Recognition && typeof Recognition.available === 'function' && 'processLocally' in new Recognition()) } catch { /* Fail closed. */ }
  let snapshot = { supported, availability: 'unavailable', checking: false, installing: false, starting: false, listening: false, interim: '', error: '' }
  let current = null, generation = 0, checkVersion = 0, onFinal = null
  const listeners = new Set()
  function publish(change) { snapshot = { ...snapshot, ...change }; listeners.forEach(listener => listener(snapshot)) }
  async function check() {
    if (!supported) return 'unavailable'
    const version = ++checkVersion
    publish({ checking: true })
    let availability = 'unavailable'
    try {
      const result = await Recognition.available({ ...options })
      if (['available', 'downloadable', 'downloading', 'unavailable'].includes(result)) availability = result
    } catch { /* Local permission policy or platform may deny availability. */ }
    if (version === checkVersion) publish({ checking: false, availability })
    return availability
  }
  async function install() {
    if (snapshot.installing || snapshot.availability !== 'downloadable' || typeof Recognition?.install !== 'function') return
    publish({ installing: true, error: '' })
    try {
      const installed = await Recognition.install({ ...options })
      if (!installed) throw new Error('Pack not installed')
      await check()
      if (snapshot.availability !== 'available' && snapshot.availability !== 'downloading') throw new Error('Pack unavailable')
    } catch { publish({ error: 'Je n’ai pas pu installer la reconnaissance vocale française. Tu peux continuer à m’écrire.' }); await check() }
    finally { publish({ installing: false }) }
  }
  function abort() {
    generation++
    const previous = current
    current = null; onFinal = null
    if (previous) {
      previous.onstart = previous.onresult = previous.onerror = previous.onend = null
      try { previous.abort() } catch { /* Already ended. */ }
    }
    publish({ starting: false, listening: false, interim: '' })
  }
  function finish(text) {
    const callback = onFinal
    abort()
    if (text.trim()) callback?.(text.trim())
  }
  function stop() { finish(snapshot.interim) }
  async function start(callback) {
    if (!supported || snapshot.starting || snapshot.listening || snapshot.installing) return
    abort()
    const token = generation
    publish({ starting: true, error: '', interim: '' })
    if (await check() !== 'available' || token !== generation) {
      if (token === generation) publish({ starting: false, error: unavailableMessage })
      return
    }
    try {
      const recognition = new Recognition()
      // Checking the actual property is mandatory: assigning an unknown field proves nothing.
      if (!('processLocally' in recognition)) throw new Error('Local mode absent')
      recognition.processLocally = true
      if (recognition.processLocally !== true) throw new Error('Local mode not confirmed')
      recognition.lang = 'fr-FR'; recognition.interimResults = true; recognition.continuous = false
      current = recognition; onFinal = callback
      recognition.onstart = () => { if (token === generation) publish({ starting: false, listening: true }) }
      recognition.onresult = event => {
        if (token !== generation) return
        const results = Array.from(event.results)
        const text = results.map(result => result[0]?.transcript || '').join(' ').trim()
        publish({ interim: text })
        if (results.length && results.every(result => result.isFinal)) finish(text)
      }
      recognition.onerror = event => {
        if (token !== generation) return
        const error = ['not-allowed', 'service-not-allowed'].includes(event.error)
          ? 'Le microphone n’est pas autorisé. Tu peux continuer à m’écrire.'
          : event.error === 'no-speech' ? 'Je n’ai pas entendu de parole. Tu peux réessayer ou m’écrire.'
            : event.error === 'language-not-supported' ? unavailableMessage
              : 'Je n’ai pas pu transcrire ta voix. Tu peux continuer à m’écrire.'
        abort(); publish({ error, ...(event.error === 'language-not-supported' ? { availability: 'unavailable' } : {}) })
      }
      recognition.onend = () => { if (token === generation) finish(snapshot.interim) }
      // start() asks for microphone permission via the browser, only after this user action.
      recognition.start()
    } catch { abort(); publish({ error: 'Je n’ai pas pu démarrer le microphone. Tu peux continuer à m’écrire.' }) }
  }
  return { getSnapshot: () => snapshot, check, install, start, stop, abort,
    subscribe(listener) { listeners.add(listener); listener(snapshot); return () => listeners.delete(listener) },
    canInstall: Boolean(supported && typeof Recognition.install === 'function'),
  }
}

export const recognition = createRecognitionService(typeof window === 'undefined' ? undefined : window)
