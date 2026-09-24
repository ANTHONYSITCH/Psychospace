import { useEffect, useRef, useState } from 'react'
import { forgetMemory, loadMemories, saveMemory } from '../api'
import { DEMO_USER_ID } from '../config'
import { missionTimestamp } from '../utils/missionClock'
import { categoryLabel, memoryCategories, memoryPayload, sourceLabel, validMemoryDraft } from '../memory'
import { dateLabel } from '../overview'
import PsychoSpacePresence from './PsychoSpacePresence'
import './Memory.css'

export default function Memory() {
  const [state, setState] = useState({ status: 'loading', memories: [] })
  const [attempt, setAttempt] = useState(0)
  const [panel, setPanel] = useState(null)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [forgotten, setForgotten] = useState(null)
  const lock = useRef(false), dialog = useRef(null), opener = useRef(null), addButton = useRef(null), stage = useRef(null)
  useEffect(() => {
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 12000)
    let active = true
    setState(previous => ({ ...previous, status: 'loading' }))
    loadMemories(controller.signal).then(memories => { if (active) setState({ status: 'ready', memories }) })
      .catch(() => { if (active) setState(previous => ({ ...previous, status: 'error' })) }).finally(() => clearTimeout(timeout))
    return () => { active = false; controller.abort(); clearTimeout(timeout) }
  }, [attempt])
  useEffect(() => {
    if (panel && !dialog.current.open) dialog.current.showModal()
    if (!panel && dialog.current.open) dialog.current.close()
    if (panel) stage.current?.focus()
  }, [panel?.mode, panel?.step, Boolean(panel)])
  function open(next) { opener.current = document.activeElement; setError(''); setNotice(''); setPanel(next) }
  function close() { if (lock.current) return; setPanel(null); setError(''); requestAnimationFrame(() => (opener.current?.isConnected ? opener.current : addButton.current)?.focus()) }
  function create() {
    open({ mode: 'form', editing: false, step: 0, draft: { id: `MEM-${crypto.randomUUID()}`, user_id: DEMO_USER_ID, category: 'support_preference', content: '', importance: 5, source: 'user', created_at: missionTimestamp() } })
  }
  function updateDraft(key, value) { setPanel(previous => ({ ...previous, draft: { ...previous.draft, [key]: value } })); setError('') }
  async function submit() {
    if (lock.current || !validMemoryDraft(panel.draft)) return
    lock.current = true; setBusy(true); setError('')
    try {
      const saved = await saveMemory(memoryPayload(panel.draft), panel.editing)
      setState(previous => ({ ...previous, memories: [...previous.memories.filter(memory => memory.id !== saved.id), saved] }))
      setNotice(panel.editing ? 'C’est corrigé.' : 'PsychoSpace l’a retenu.')
      setPanel({ mode: 'read', memory: saved })
    } catch { setError('Je n’ai pas réussi à enregistrer cette information.') }
    finally { lock.current = false; setBusy(false) }
  }
  async function forget() {
    if (lock.current) return
    lock.current = true; setBusy(true); setError('')
    try {
      await forgetMemory(panel.memory.id)
      setForgotten(panel.memory.id)
      if (!matchMedia('(prefers-reduced-motion: reduce)').matches) await new Promise(resolve => setTimeout(resolve, 220))
      setState(previous => ({ ...previous, memories: previous.memories.filter(memory => memory.id !== panel.memory.id) }))
      setForgotten(null)
      setNotice('C’est oublié.')
      lock.current = false; close()
    } catch { setError('Je n’ai pas réussi à l’oublier pour le moment.') }
    finally { lock.current = false; setBusy(false) }
  }
  const draft = panel?.draft, memory = panel?.memory
  return <section className="memory-page">
    <header className="page-header"><div><span className="eyebrow">UNE CONSTELLATION PERSONNELLE</span><h1>Mémoire<span className="heading-dot">.</span></h1></div></header>
    <div className="memory-intro"><h2>Ce que PsychoSpace garde de toi</h2><p>Ces informations t’appartiennent.<br />Tu peux les corriger ou demander à PsychoSpace de les oublier.</p></div>
    <p className="memory-control">Tu restes maître de ce que PsychoSpace retient.</p>
    <p className="memory-notice" role="status">{notice}</p>
    {state.status === 'loading' && <p role="status">PsychoSpace retrouve tes souvenirs…</p>}
    {state.status === 'error' && <div role="alert"><p>Je n’arrive pas à retrouver tes souvenirs pour le moment.</p><button className="primary-button" onClick={() => setAttempt(value => value + 1)}>Réessayer</button></div>}
    {state.status === 'ready' && <>
      {!state.memories.length ? <div className="memory-empty"><PsychoSpacePresence state="attentive" /><h2>PsychoSpace ne garde encore rien de personnel ici.</h2><p>Tu peux choisir ce que tu veux lui apprendre.</p></div> :
        <div className="memory-constellation" aria-label="Tes souvenirs">
          <div className="memory-center" aria-hidden="true"><PsychoSpacePresence state="attentive" /><span>Des fragments de toi</span></div>
          <div className="memory-fragments">{state.memories.map((item, index) => <button className={`memory-fragment${forgotten === item.id ? ' memory-forgotten' : ''}`} key={item.id} style={{ '--importance': item.importance, '--offset': `${index % 2 ? -10 : 10}px` }} onClick={() => open({ mode: 'read', memory: item })} aria-label={`${categoryLabel(item.category)} : ${item.content}`}><span className="memory-star" aria-hidden="true" /><span className="memory-category">{categoryLabel(item.category)}</span><span className="memory-excerpt">{item.content}</span><span className="memory-open" aria-hidden="true">Ouvrir ce souvenir ↗</span></button>)}</div>
        </div>}
      <button ref={addButton} className="primary-button memory-add" onClick={create}>{state.memories.length ? 'Ajouter quelque chose que PsychoSpace peut retenir' : 'Ajouter un premier souvenir'}</button>
    </>}
    <details className="memory-privacy"><summary>Comment fonctionne ma mémoire ?</summary><p>PsychoSpace utilise uniquement les souvenirs enregistrés ici pour personnaliser certaines conversations et propositions.</p><p>Tu peux les revoir, les corriger ou les oublier.</p></details>
    <dialog ref={dialog} className="memory-dialog" aria-labelledby="memory-panel-title" onCancel={event => { event.preventDefault(); close() }}>
      {panel && <><button className="memory-close" disabled={busy} onClick={close}>Fermer</button><div ref={stage} tabIndex="-1" className="memory-stage">
        {panel.mode === 'read' && <><span className="eyebrow">UN FRAGMENT DE TOI</span><h2 id="memory-panel-title">{categoryLabel(memory.category)}</h2><p className="memory-content">{memory.content}</p><p>Importance pour l’accompagnement : {memory.importance} / 10</p><p className="memory-origin">{sourceLabel(memory.source)} · {dateLabel(memory.created_at)}</p><div className="memory-actions"><button className="primary-button" onClick={() => { setError(''); setPanel({ mode: 'form', editing: true, draft: { ...memory }, step: 0 }) }}>Corriger</button><button className="memory-secondary" onClick={() => { setError(''); setPanel({ mode: 'forget', memory }) }}>Oublier</button></div></>}
        {panel.mode === 'forget' && <><h2 id="memory-panel-title">Tu veux vraiment que PsychoSpace oublie cette information ?</h2><p className="memory-content">{memory.content}</p><div className="memory-actions"><button className="primary-button" disabled={busy} onClick={forget}>{busy ? 'Oubli en cours…' : 'Oui, oublier'}</button><button className="memory-secondary" disabled={busy} onClick={() => { setError(''); setPanel({ mode: 'read', memory }) }}>Non, la garder</button></div></>}
        {panel.mode === 'form' && <form onSubmit={event => { event.preventDefault(); if (panel.step === 3) submit(); else setPanel(previous => ({ ...previous, step: previous.step + 1 })) }}>
          <span className="eyebrow">{panel.editing ? 'CORRIGER UN SOUVENIR' : 'UN NOUVEAU SOUVENIR'} · {panel.step + 1} / 4</span>
          <h2 id="memory-panel-title">{['Où se place ce souvenir ?', 'Qu’aimerais-tu que PsychoSpace retienne ?', 'À quel point cette information est importante pour toi ?', 'C’est bien ce que tu veux partager ?'][panel.step]}</h2>
          {panel.step === 0 && <label>Catégorie<select aria-label="Catégorie" value={draft.category} onChange={event => updateDraft('category', event.target.value)}>{!memoryCategories[draft.category] && <option value={draft.category}>Un repère personnel</option>}{Object.entries(memoryCategories).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>}
          {panel.step === 1 && <label>Information<textarea aria-label="Information" required value={draft.content} onChange={event => updateDraft('content', event.target.value)} placeholder="Par exemple : marcher quelques minutes m’aide quand j’ai besoin de souffler." rows="5" /></label>}
          {panel.step === 2 && <fieldset><legend>Importance pour l’accompagnement</legend><div className="memory-scale">{Array.from({ length: 10 }, (_, index) => index + 1).map(value => <label key={value}><input type="radio" name="importance" checked={draft.importance === value} onChange={() => updateDraft('importance', value)} value={value} /><span>{value}</span></label>)}</div><p className="memory-origin">1 : peu important · 10 : très important</p></fieldset>}
          {panel.step === 3 && <><p className="memory-category">{categoryLabel(draft.category)}</p><p className="memory-content">{draft.content}</p><p>Importance pour l’accompagnement : {draft.importance} / 10</p></>}
          <div className="memory-actions">{panel.step > 0 && <button type="button" className="memory-secondary" disabled={busy} onClick={() => { setError(''); setPanel(previous => ({ ...previous, step: previous.step - 1 })) }}>Retour</button>}<button className="primary-button" type="submit" disabled={busy || (panel.step === 1 && !draft.content.trim()) || (panel.step === 3 && !validMemoryDraft(draft))}>{busy ? 'Enregistrement…' : panel.step === 3 ? 'Confirmer' : 'Continuer'}</button></div>
        </form>}
      </div>{error && <p role="alert" className="memory-error">{error}</p>}{notice && <p role="status">{notice}</p>}</>}
    </dialog>
  </section>
}
