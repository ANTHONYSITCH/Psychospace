import { useEffect, useState } from 'react'
import { loadOverview } from '../api'
import { dateLabel, greeting, latest, metricDefinitions, number, percent, rhythmText } from '../overview'
import PsychoSpacePresence from './PsychoSpacePresence'
import Icon from './Icon'

export default function Overview() {
  const [request, setRequest] = useState(0)
  const [result, setResult] = useState({ status: 'loading' })
  const [expanded, setExpanded] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    let active = true
    setResult({ status: 'loading' })
    const timeout = setTimeout(() => controller.abort(), 12000)
    loadOverview(controller.signal).then(data => {
      if (active) setResult({ status: data.profile ? 'ready' : 'empty', data })
    }).catch(() => { if (active) setResult({ status: 'error' }) }).finally(() => clearTimeout(timeout))
    return () => { active = false; clearTimeout(timeout); controller.abort() }
  }, [request])

  const { data, status } = result
  const drift = data ? latest(data.drift, 'detected_at') : null
  const checkin = data ? latest(data.checkins, 'timestamp') : null
  const hasDrift = !!drift && drift.status !== 'resolved'
  return <>
    <header className="page-header"><div><span className="eyebrow">TON ESPACE PERSONNEL</span><h1>Vue d'ensemble<span className="heading-dot">.</span></h1></div>
      <div className="record-date"><span className="eyebrow">DERNIER BILAN</span><span>{dateLabel(checkin?.timestamp)}</span></div>
    </header>
    <section className="companion-stage" aria-label="Présence PsychoSpace" aria-busy={status === 'loading'}>
      <div className="stage-top"><span className="eyebrow">UN PEU D’ESPACE POUR SOUFFLER</span><span className="connection"><i className={status === 'ready' ? 'connected' : ''} />{status === 'ready' ? 'À tes côtés' : status === 'loading' ? 'Connexion en cours' : 'Quand tu le souhaites'}</span></div>
      <PsychoSpacePresence state={status === 'ready' && hasDrift ? 'drift' : 'idle'} level={drift?.level} />
      {status === 'loading' && <div className="hero-copy" role="status"><h2>Ton espace se prépare.</h2><p>Un instant pour retrouver tes repères.</p><span className="loading-dots" aria-hidden="true">· · ·</span></div>}
      {status === 'error' && <div className="hero-copy" role="alert"><h2>Une petite pause.</h2><p>Le cœur de PsychoSpace est momentanément indisponible.</p><button className="primary-button" onClick={() => setRequest(r => r + 1)}>Réessayer <Icon name="arrow" /></button></div>}
      {status === 'empty' && <div className="hero-copy"><h2>Ton espace t’attend.</h2><p>Aucun profil n’est encore disponible. Tes repères apparaîtront ici.</p><button className="primary-button" onClick={() => setRequest(r => r + 1)}>Actualiser <Icon name="arrow" /></button></div>}
      {status === 'ready' && <div className="hero-copy">
        <span className="presence-caption">ICI, À TON RYTHME</span>
        <h2>{greeting()} <em>{data.profile.first_name}.</em></h2>
        <p>{rhythmText(drift)}<br /><span className="soft-copy">Tu choisis ce qui te convient.</span></p>
        {drift ? <button className="primary-button" aria-expanded={expanded} aria-controls="drift-explanation" onClick={() => setExpanded(!expanded)}>{expanded ? 'Moins de détails' : 'Pourquoi ?'}<Icon name="arrow" /></button>
          : <p className="empty-note">Aucun changement de rythme enregistré pour le moment.</p>}
      </div>}
      <div className="stage-bottom"><span>TON RYTHME. TON CHOIX.</span><span className="small-orbit" aria-hidden="true">◌</span><span>UNE PRÉSENCE À TES CÔTÉS.</span></div>
    </section>
    {status === 'ready' && expanded && drift && <section id="drift-explanation" className="explanation" aria-labelledby="explanation-title">
      <div><span className="eyebrow">POUR MIEUX COMPRENDRE</span><h3 id="explanation-title">Ce qui a changé</h3><span className="drift-tag">{percent(drift.drift_score)} · écart par rapport à ton rythme habituel</span></div>
      <div><p lang="fr">{drift.explanation || 'Aucune explication n’a été enregistrée pour ce changement.'}</p><p className="explanation-meta">Observé le {dateLabel(drift.detected_at)} · Ces observations décrivent une évolution par rapport à tes habitudes.</p></div>
    </section>}
    {status === 'ready' && <section className="rhythm-section" aria-labelledby="rhythm-title">
      <div className="section-heading"><div><span className="eyebrow">QUELQUES REPÈRES, UNE VUE D’ENSEMBLE</span><h2 id="rhythm-title">Ton rythme en quelques repères</h2></div><span className="legend"><i /> État récent <b /> Rythme habituel</span></div>
      {!checkin && <p className="empty-note">Aucun bilan pour le moment. Tes repères récents apparaîtront ici.</p>}
      <div className="metrics">{metricDefinitions.map(metric => {
        const current = checkin?.[metric.key], usual = data.baseline?.[metric.baseline]
        const maximum = Math.max(current || 0, usual || 0, 1) * 1.2
        return <article className="metric" key={metric.key}>
          <h3><Icon name={metric.icon} />{metric.label}</h3>
          <p className="metric-value">{number(current)}<span>{metric.unit}</span></p>
          <div className="rhythm-track" aria-hidden="true"><span style={{ width: Number.isFinite(current) ? `${current / maximum * 100}%` : 0 }} />{Number.isFinite(usual) && <i style={{ left: `${usual / maximum * 100}%` }} />}</div>
          <p className="usual">D’habitude <strong>{number(usual)}</strong> {metric.unit}</p>
        </article>
      })}</div>
      {!data.baseline && <p className="empty-note">Ton rythme habituel n’est pas encore disponible.</p>}
    </section>}
    <footer className="page-footer"><span><Icon name="lock" /> Tes données restent à bord.</span><span>Mission de démonstration · {checkin ? `données d’exemple du ${dateLabel(checkin.timestamp)}` : 'tes repères, à ton rythme'}</span></footer>
  </>
}
