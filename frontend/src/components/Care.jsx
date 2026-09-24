import { useEffect, useRef, useState } from 'react'
import { loadInterventions, patchIntervention } from '../api'
import { interventionHistory, interventionLabel, interventionState, relevantIntervention } from '../care'
import { dateLabel } from '../overview'
import PsychoSpacePresence from './PsychoSpacePresence'
import './Care.css'

export default function Care() {
  const [state, setState] = useState({ status: 'loading', items: [] })
  const [attempt, setAttempt] = useState(0)
  const [selected, setSelected] = useState(null)
  const [deferred, setDeferred] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const lock = useRef(false), heading = useRef(null)
  useEffect(() => {
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 12000)
    let active = true
    setState(previous => ({ ...previous, status: 'loading' }))
    loadInterventions(controller.signal).then(items => {
      if (active) { setState({ status: 'ready', items }); setSelected(relevantIntervention(items)?.id || null) }
    }).catch(() => { if (active) setState(previous => ({ ...previous, status: 'error' })) }).finally(() => clearTimeout(timeout))
    return () => { active = false; controller.abort(); clearTimeout(timeout) }
  }, [attempt])
  const chosen = state.items.find(item => item.id === selected)
  function choose(item) { setSelected(item.id); setDeferred(false); setError(''); setNotice(''); requestAnimationFrame(() => heading.current?.focus()) }
  async function save(change) {
    if (lock.current) return
    lock.current = true; setBusy(true); setError(''); setNotice('')
    try {
      const saved = await patchIntervention(chosen.id, change)
      setState(previous => ({ ...previous, items: previous.items.map(item => item.id === saved.id ? saved : item) }))
      setNotice(saved.completed ? 'C’est noté. Merci de m’avoir tenu au courant.' : 'C’est noté. Ce moment reste à ton rythme.')
      requestAnimationFrame(() => heading.current?.focus())
    } catch { setError('Je n’ai pas réussi à enregistrer ton choix.') }
    finally { lock.current = false; setBusy(false) }
  }
  return <section className="care-page">
    <header className="page-header"><div><span className="eyebrow">UN PEU D’ESPACE POUR TOI</span><h1>Accompagnement<span className="heading-dot">.</span></h1></div></header>
    <p className="care-control">Aucune proposition ne s’impose à toi.</p>
    {state.status === 'loading' && <p role="status" className="care-message">PsychoSpace retrouve tes accompagnements…</p>}
    {state.status === 'error' && <div role="alert" className="care-message"><p>Je n’arrive pas à retrouver tes accompagnements pour le moment.</p><button className="primary-button" onClick={() => setAttempt(value => value + 1)}>Réessayer</button></div>}
    {state.status === 'ready' && <>
      <div className="care-main"><div className="care-presence"><PsychoSpacePresence state="attentive" /><span>À ton rythme.</span></div>
        <div className="care-proposal">
          {!chosen ? <><h2>Rien à te proposer pour le moment.</h2><p>PsychoSpace reste attentif à ton rythme.</p></> : deferred ? <><h2 ref={heading} tabIndex="-1">On peut y revenir plus tard.</h2><p>Cette proposition reste disponible, quand tu le souhaites.</p><button className="care-secondary" onClick={() => { setDeferred(false); requestAnimationFrame(() => heading.current?.focus()) }}>Retrouver cette proposition</button></> : <>
            <span className="care-state">{interventionState(chosen)}</span>
            <h2 ref={heading} tabIndex="-1">{chosen.completed ? 'Un moment que tu as choisi.' : chosen.accepted ? 'Tu as choisi ce moment pour toi.' : 'J’ai une idée pour toi.'}</h2>
            <h3>{interventionLabel(chosen.type)}</h3>
            <p className="care-api-message">{chosen.message}</p>
            <p className="care-date">Proposé le {dateLabel(chosen.created_at)}</p>
            {chosen.accepted && !chosen.completed && <p className="care-invitation">Quand tu veux, tu peux me dire que c’est terminé.</p>}
            <div className="care-actions">{!chosen.accepted && !chosen.completed && <><button className="primary-button" disabled={busy} onClick={() => save({ accepted: true })}>Ça me va</button><button className="care-secondary" disabled={busy} onClick={() => { setDeferred(true); setError(''); setNotice(''); requestAnimationFrame(() => heading.current?.focus()) }}>Pas maintenant</button></>}{chosen.accepted && !chosen.completed && <button className="primary-button" disabled={busy} onClick={() => save({ completed: true })}>J’ai terminé</button>}</div>
            {chosen.drift_event_id && <p className="care-context">Cette proposition fait suite à une évolution que PsychoSpace a remarquée. <a href="#evolution">Voir pourquoi</a></p>}
          </>}
          <p className="care-notice" role="status">{busy ? 'Ton choix s’enregistre…' : notice}</p>{error && <p role="alert" className="care-error">{error}</p>}
        </div>
      </div>
      {state.items.length > 0 && <section className="care-history" aria-labelledby="care-history-title"><span className="eyebrow">LES MOMENTS PROPOSÉS</span><h2 id="care-history-title">Au fil des jours</h2><ol>{interventionHistory(state.items).map(item => <li key={item.id}><button disabled={busy} aria-current={item.id === selected ? 'true' : undefined} onClick={() => choose(item)}><time dateTime={item.created_at}>{dateLabel(item.created_at)}</time><span>{interventionLabel(item.type)}</span><small>{interventionState(item)}</small></button></li>)}</ol></section>}
    </>}
  </section>
}
