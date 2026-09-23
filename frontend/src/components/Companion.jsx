import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { getChatHistory, loadProfile, sendChatMessage } from '../api'
import PsychoSpacePresence from './PsychoSpacePresence'
import Icon from './Icon'
import './Companion.css'
import { voice } from '../services/voice'

// POST replies omit id; timestamp/content also identify the same reply after GET.
const speechKey = item => item ? JSON.stringify([item.timestamp || item.id, item.content]) : null

export default function Companion() {
  const [history, setHistory] = useState([])
  const [name, setName] = useState('')
  const [draft, setDraft] = useState('')
  const [phase, setPhase] = useState('loading')
  const [late, setLate] = useState(false)
  const [error, setError] = useState(null)
  const [receipt, setReceipt] = useState(null)
  const [unread, setUnread] = useState(false)
  const [voiceEnabled, setVoiceEnabled] = useState(() => voice.getEnabled())
  const [speech, setSpeech] = useState(() => voice.getSnapshot())
  const [newReply, setNewReply] = useState(null)
  const enabledRef = useRef(voiceEnabled)
  const spokenReply = useRef(null)
  const busy = useRef(false)
  const mounted = useRef(true)
  const transcript = useRef(null)
  const nearBottom = useRef(true)
  const firstLoad = useRef(true)
  const previousAttempt = useRef(null)
  const sending = phase === 'sending'

  useEffect(() => {
    const unsubscribe = voice.subscribe(setSpeech)
    return () => { unsubscribe(); voice.stop() }
  }, [])
  useEffect(() => {
    // Only a newly confirmed POST reply that is already in the visible transcript.
    // History loading, navigation and preference changes never trigger speech.
    if (!newReply || spokenReply.current === speechKey(newReply)) return
    if (speechKey(receipt?.reply) !== speechKey(newReply) && !history.some(item => speechKey(item) === speechKey(newReply))) return
    spokenReply.current = speechKey(newReply)
    if (enabledRef.current) voice.speak(newReply.content, speechKey(newReply))
  }, [newReply, history, receipt])

  function toggleVoice(enabled) {
    enabledRef.current = enabled; setVoiceEnabled(enabled); voice.setEnabled(enabled)
  }
  function voiceControl(item) {
    const active = speech.activeId === speechKey(item) && (speech.speaking || speech.pending)
    return <button className="voice-listen" type="button" disabled={!voiceEnabled || !speech.supported || !speech.selectedVoice || sending} aria-label={active ? 'Arrêter la lecture de cette réponse' : 'Écouter cette réponse'} onClick={() => active ? voice.stop() : voice.speak(item.content, speechKey(item))}>{active ? 'Arrêter' : 'Écouter'}</button>
  }

  useEffect(() => {
    mounted.current = true
    const controller = new AbortController()
    loadProfile(controller.signal).then(profile => { if (mounted.current) setName(profile?.first_name || '') }).catch(() => {})
    getChatHistory(controller.signal).then(items => {
      if (mounted.current) { setHistory(items); setPhase('ready') }
    }).catch(() => { if (mounted.current && !controller.signal.aborted) setPhase('history-error') })
    return () => { mounted.current = false; controller.abort() }
  }, [])
  useEffect(() => {
    setLate(false)
    if (!sending) return
    const timer = setTimeout(() => setLate(true), 20000)
    return () => clearTimeout(timer)
  }, [sending])
  useLayoutEffect(() => {
    const area = transcript.current
    if (!area) return
    if (nearBottom.current || firstLoad.current) {
      area.scrollTo({ top: area.scrollHeight, behavior: firstLoad.current || window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
      setUnread(false)
    } else setUnread(true)
    firstLoad.current = false
  }, [history, receipt])

  async function reload() {
    if (busy.current) return
    busy.current = true
    setPhase('refreshing')
    try {
      const items = await getChatHistory()
      if (!mounted.current) return
      setHistory(items); setReceipt(null); setPhase('ready'); setError(null)
    } catch { if (mounted.current) setPhase(receipt ? 'sync-error' : 'history-error') }
    finally { busy.current = false }
  }

  async function send(event) {
    event?.preventDefault()
    const message = draft.trim()
    if (busy.current || !message || !['ready', 'send-error'].includes(phase)) return
    voice.stop()
    busy.current = true
    setPhase('sending'); setError(null)
    try {
      // Reconcile an ambiguous failed request before an explicit retry.
      if (previousAttempt.current) {
        const items = await getChatHistory()
        const attempt = previousAttempt.current
        const recovered = items.some((item, index) => !attempt.ids.has(item.id)
          && item.role === 'user' && item.content === attempt.message && items[index + 1]?.role === 'assistant')
        setHistory(items)
        if (recovered && message === attempt.message) {
          setDraft(''); setPhase('ready'); previousAttempt.current = null; return
        }
      }
      previousAttempt.current = { message, ids: new Set(history.map(item => item.id)) }
      const reply = await sendChatMessage(message)
      if (!mounted.current) return
      previousAttempt.current = null
      setDraft('')
      setPhase('refreshing')
      // This is the actual POST receipt, displayed only after backend confirmation.
      setReceipt({ message, reply })
      setNewReply(reply)
      try {
        const items = await getChatHistory()
        if (mounted.current) { setHistory(items); setReceipt(null); setPhase('ready') }
      } catch { if (mounted.current) setPhase('sync-error') }
    } catch (failure) {
      if (mounted.current) {
        setError(failure.status === 503 ? 'engine' : 'connection')
        setPhase('send-error')
      }
    } finally { busy.current = false }
  }

  function jumpToRecent() {
    nearBottom.current = true
    transcript.current?.scrollTo({ top: transcript.current.scrollHeight, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
    setUnread(false)
  }
  const canCompose = ['ready', 'send-error'].includes(phase)
  return <>
    <header className="page-header"><div><span className="eyebrow">UN ESPACE POUR SE PARLER</span><h1>Compagnon<span className="heading-dot">.</span></h1></div><span className="companion-local"><Icon name="lock" /> Conversation locale</span></header>
    <section className="conversation-space" aria-label="Échanger avec PsychoSpace">
      <div className="conversation-presence"><PsychoSpacePresence state={sending ? 'thinking' : speech.speaking ? 'speaking' : 'attentive'} />
        <p className="conversation-status" role="status" aria-live="polite">{sending ? late ? 'Le compagnon local se prépare… Je prends le temps de te répondre.' : 'PsychoSpace réfléchit…' : speech.speaking ? 'PsychoSpace te répond à voix haute.' : phase === 'loading' ? 'Je retrouve notre conversation…' : 'Je t’écoute.'}</p>
      </div>
      <div className="voice-preference"><label><input type="checkbox" checked={voiceEnabled} disabled={!speech.supported} onChange={event => toggleVoice(event.target.checked)} />Réponses vocales</label><span>{voiceEnabled ? 'Voix activée · le texte reste visible' : 'Active les réponses vocales si tu le souhaites.'}</span>{(speech.pending || speech.speaking) && <button type="button" className="voice-listen" onClick={() => voice.stop()}>Arrêter</button>}</div>
      {(!speech.supported || !speech.selectedVoice || speech.error) && <p className="voice-notice" aria-live="polite">{speech.error || 'La voix n’est pas disponible sur cet appareil.'}</p>}
      {phase === 'history-error' ? <div className="conversation-error" role="alert"><p>Je n’arrive pas à retrouver notre conversation pour le moment.</p><button type="button" className="text-button" onClick={reload}>Réessayer</button></div> : null}
      <div className="transcript" ref={transcript} tabIndex="0" role="region" aria-label="Notre conversation" onScroll={() => {
        const area = transcript.current
        nearBottom.current = area.scrollHeight - area.scrollTop - area.clientHeight < 70
        if (nearBottom.current) setUnread(false)
      }}>
        {!history.length && phase === 'ready' && !receipt && <div className="conversation-empty"><h2>Je suis là{name ? `, ${name}` : ''}.</h2><p>Tu peux me parler comme tu le ferais naturellement.<br />Ou simplement prendre un moment.</p></div>}
        {history.map(item => <article key={item.id} className={`transcript-entry transcript-entry--${item.role}`}><h2>{item.role === 'user' ? name || 'Toi' : 'PsychoSpace'}</h2><p>{item.content}</p>{item.role === 'assistant' && voiceControl(item)}</article>)}
        {receipt && <><article className="transcript-entry transcript-entry--user"><h2>{name || 'Toi'}</h2><p>{receipt.message}</p></article><article className="transcript-entry transcript-entry--assistant"><h2>PsychoSpace</h2><p>{receipt.reply.content}</p>{voiceControl(receipt.reply)}</article></>}
      </div>
      {unread && <button type="button" className="recent-button" onClick={jumpToRecent}>Revenir aux derniers échanges ↓</button>}
      {phase === 'send-error' && <div className="conversation-error" role="alert"><p>{error === 'engine' ? 'Je n’arrive pas à accéder à mon moteur de conversation pour le moment.' : 'Je n’ai pas pu confirmer l’envoi de ton message.'}</p><p>Ton texte reste dans la zone de saisie. Tu peux réessayer ; je vérifierai d’abord notre conversation.</p></div>}
      {phase === 'sync-error' && <div className="conversation-error" role="alert"><p>La réponse est arrivée, mais je n’arrive pas à actualiser notre conversation.</p><button className="text-button" type="button" onClick={reload}>Actualiser la conversation</button></div>}
      <form className="conversation-composer" onSubmit={send}>
        <label htmlFor="companion-message">Ce que tu souhaites partager</label>
        <textarea id="companion-message" rows="3" placeholder="Dis-moi ce qui te passe par la tête…" value={draft} disabled={!canCompose} onChange={event => setDraft(event.target.value)} onKeyDown={event => {
          if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); send() }
        }} />
        <div className="composer-actions"><span>Entrée pour envoyer · Maj + Entrée pour une nouvelle ligne</span><button className="primary-button" disabled={!canCompose || !draft.trim()} type="submit">{sending ? 'Je prends un instant…' : phase === 'send-error' ? 'Réessayer' : 'Envoyer'}{!sending && <Icon name="arrow" />}</button></div>
      </form>
      <details className="conversation-privacy"><summary>Ce que PsychoSpace utilise pour te répondre</summary><ul><li>Ton profil</li><li>Ton rythme habituel</li><li>Tes bilans récents</li><li>Les souvenirs que tu as autorisés</li><li>Les changements détectés</li></ul><p>Tu gardes le contrôle de ce que PsychoSpace mémorise.</p></details>
    </section>
  </>
}
