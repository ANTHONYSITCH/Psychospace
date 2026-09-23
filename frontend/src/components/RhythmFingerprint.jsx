import { useEffect, useRef, useState } from 'react'
import { loadEvolution } from '../api'
import { latest, percent } from '../overview'
import { fullDate, metricValue } from '../evolution'
import { contourPoints, dimensionDescription, dimensions, fingerprintData, organicPath } from '../fingerprint'
import PsychoSpacePresence from './PsychoSpacePresence'
import './RhythmFingerprint.css'

export default function RhythmFingerprint() {
  const [state, setState] = useState({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const [selection, setSelection] = useState('sleep_hours')
  const [progress, setProgress] = useState(1)
  const [playing, setPlaying] = useState(false)
  const frame = useRef(null)
  function comparison() { cancelAnimationFrame(frame.current); setProgress(1); setPlaying(false) }
  useEffect(() => {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 12000)
    let active = true
    setState({ status: 'loading' })
    loadEvolution(controller.signal).then(data => {
      if (!active) return
      const drift = latest(data.drift, 'detected_at')
      setState({ status: 'ready', drift, ...fingerprintData(data.checkins, data.baseline, drift) })
    }).catch(() => { if (active) setState({ status: 'error' }) }).finally(() => clearTimeout(timeout))
    return () => { active = false; controller.abort(); clearTimeout(timeout); cancelAnimationFrame(frame.current) }
  }, [attempt])
  useEffect(() => {
    const preference = matchMedia('(prefers-reduced-motion: reduce)')
    const change = () => { if (preference.matches) comparison() }
    preference.addEventListener('change', change)
    return () => preference.removeEventListener('change', change)
  }, [])
  function showChange() {
    comparison()
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return
    setProgress(0); setPlaying(true)
    const start = performance.now()
    const tick = now => {
      const elapsed = Math.min(1, (now - start) / 1800)
      setProgress(elapsed * elapsed * (3 - 2 * elapsed))
      if (elapsed < 1) frame.current = requestAnimationFrame(tick)
      else setPlaying(false)
    }
    frame.current = requestAnimationFrame(tick)
  }
  const chosen = state.values?.find(value => value.key === selection)
  const points = state.ready ? contourPoints(state.values, progress) : []
  return <section className="fingerprint" aria-labelledby="fingerprint-title">
    <header className="page-header"><div><span className="eyebrow">DEUX EMPREINTES, UNE MÊME HISTOIRE</span><h1 id="fingerprint-title">Mon empreinte<span className="heading-dot">.</span></h1></div></header>
    <div className="evolution-intro"><h2>Un rythme se transforme au fil des jours.</h2><p>Les petites variations prennent sens dans la durée.</p></div>
    {state.status === 'loading' && <p role="status" className="evolution-message">PsychoSpace reconstitue ton empreinte...</p>}
    {state.status === 'error' && <div role="alert" className="evolution-message"><p>Je n’arrive pas à reconstruire cette évolution pour le moment.</p><button className="primary-button" onClick={() => setAttempt(value => value + 1)}>Réessayer</button></div>}
    {state.status === 'ready' && !state.ready && <p className="evolution-message">Il me faut encore quelques bilans pour comparer ton rythme.</p>}
    {state.status === 'ready' && state.ready && <>
      <div className="fingerprint-legend"><span><i className="usual-key" />Moi habituellement</span><span><i className="recent-key" />Moi récemment</span></div>
      <div className="fingerprint-layout">
        <div className="fingerprint-art">
          <svg viewBox="0 0 600 560" role="img" aria-labelledby="fingerprint-svg-title fingerprint-svg-desc">
            <title id="fingerprint-svg-title">Empreinte de rythme : habituel et récent</title>
            <desc id="fingerprint-svg-desc">Un contour pointillé représente tes habitudes. Le contour continu représente la moyenne des trois bilans précédant la détection. Une valeur plus élevée étend la forme, une valeur plus basse la rapproche du centre. Les boutons ci-dessous permettent de lire chaque comparaison.</desc>
            <defs><radialGradient id="fingerprint-halo"><stop stopColor="#c9d9b3" stopOpacity=".11" /><stop offset="1" stopColor="#c9d9b3" stopOpacity="0" /></radialGradient></defs>
            <ellipse cx="300" cy="280" rx="275" ry="260" fill="url(#fingerprint-halo)" />
            <path className="fingerprint-usual" d={organicPath(contourPoints(state.values))} />
            <path className="fingerprint-recent" data-progress={progress} d={organicPath(points)} />
            {state.values.map((value, index) => {
              const point = points[index], angle = -Math.PI / 2 + index * Math.PI * 2 / 7
              return <g key={value.key} aria-hidden="true">
                {value.affected && <circle className="affected-ring" data-signal={value.key} cx={point.x} cy={point.y} r="10" />}
                <circle cx={point.x} cy={point.y} r={value.key === selection ? 5 : 3} fill="#e0d1ae" />
                <text x={300 + Math.cos(angle) * 246} y={284 + Math.sin(angle) * 246} textAnchor="middle" className="fingerprint-label">{index + 1}</text>
              </g>
            })}
          </svg>
          <div className="fingerprint-presence"><PsychoSpacePresence state="attentive" /></div>
        </div>
        <div className="fingerprint-detail" aria-live="polite">
          <span className="eyebrow">UN REPÈRE DE TON RYTHME</span><h2>{chosen.label}</h2>
          <dl><div><dt>Habituellement</dt><dd data-value="usual">{metricValue(chosen, chosen.usual)}</dd></div><div><dt>Récemment</dt><dd data-value="recent">{metricValue(chosen, chosen.recent)}</dd></div></dl>
          <p>{dimensionDescription(chosen)}</p>
          {chosen.affected && <p className="fingerprint-affected-note">Ce repère fait partie des changements répétés remarqués par PsychoSpace.</p>}
        </div>
      </div>
      <div className="fingerprint-dimensions" aria-label="Choisir une dimension">{state.values.map((value, index) => <button key={value.key} aria-pressed={selection === value.key} onClick={() => setSelection(value.key)}><span>{index + 1}</span>{value.label}{value.affected && <i aria-label="Changement répété" className="dimension-marker" />}</button>)}</div>
      <p className="fingerprint-marker-legend"><i className="dimension-marker" /> Dimensions qui ont changé de façon répétée</p>
      <div className="fingerprint-actions"><button className="primary-button" onClick={showChange}>Voir le changement</button><button className="fingerprint-compare" onClick={comparison}>Revenir à la comparaison</button><span role="status">{playing ? 'Le contour récent se dessine…' : 'Les deux empreintes sont superposées.'}</span></div>
      <p className="fingerprint-window">Moyenne des trois bilans du {fullDate(state.records[0].timestamp)} au {fullDate(state.records.at(-1).timestamp)}, disponibles au moment de la détection. Les bilans suivants ne sont pas inclus.</p>
      <p className="fingerprint-window">Les contours rapprochent des unités différentes. Les valeurs ci-dessus restent exprimées dans leur unité d’origine.</p>
      <div className="fingerprint-moment"><h2>PsychoSpace a remarqué cette évolution le {fullDate(state.drift.detected_at)}.</h2><details><summary>Pourquoi ?</summary><p>{state.drift.explanation || 'Aucune explication n’a été enregistrée.'}</p><ul>{(state.drift.affected_signals || []).map((signal, index) => <li key={signal}>{dimensions.find(value => value.key === signal)?.label || ({ movement: 'Mouvement', heart_rate: 'Rythme cardiaque', spo2: 'Oxygénation' })[signal] || `Autre repère observé ${index + 1}`}</li>)}</ul><p>Indice d’évolution : {percent(state.drift.drift_score)}</p><small>Cet indice décrit l’écart observé par rapport à ton rythme personnel. Ce n’est pas une probabilité médicale.</small></details></div>
    </>}
  </section>
}
