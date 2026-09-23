import { useEffect, useState } from 'react'
import { loadEvolution } from '../api'
import { latest, number, percent } from '../overview'
import { dailyRecords, fullDate, metricValue, monthLabel, recentSummary, rhythmMetrics, timeline, tracePath, visualDeviation } from '../evolution'
import PsychoSpacePresence from './PsychoSpacePresence'
import './Evolution.css'

const signalNames = { sleep_hours: 'Sommeil', energy: 'Énergie', fatigue: 'Fatigue', activity_minutes: 'Activité', mood: 'Humeur', stress: 'Pression ressentie', social_level: 'Échanges', heart_rate: 'Rythme cardiaque', spo2: 'Oxygénation', movement: 'Mouvement' }

export default function Evolution() {
  const [state, setState] = useState({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const [month, setMonth] = useState('')
  const [selection, setSelection] = useState('')
  useEffect(() => {
    let active = true
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 12000)
    setState({ status: 'loading' })
    loadEvolution(controller.signal).then(data => {
      if (!active) return
      const days = dailyRecords(data.checkins)
      setState({ status: 'ready', ...data, days })
      setMonth(days.at(-1)?.day.slice(0, 7) || '')
      setSelection(days.at(-1)?.day || '')
    }).catch(() => { if (active) setState({ status: 'error' }) }).finally(() => clearTimeout(timeout))
    return () => { active = false; controller.abort(); clearTimeout(timeout) }
  }, [attempt])
  const days = state.days?.filter(day => day.day.startsWith(month)) || []
  const chosen = days.find(day => day.day === selection) || days.at(-1)
  const drift = state.drift ? latest(state.drift, 'detected_at') : null
  const months = [...new Set(state.days?.map(day => day.day.slice(0, 7)) || [])]
  const width = Math.max(840, days.length * 53)
  const coordinates = days.length ? timeline(days, state.baseline, width) : null
  const driftVisible = coordinates && drift && Date.parse(drift.detected_at) >= coordinates.start && Date.parse(drift.detected_at) <= coordinates.end
  const missing = rhythmMetrics.filter(metric => !Number.isFinite(state.baseline?.[metric.baseline]) || state.baseline[metric.baseline] <= 0)
  return <>
    <header className="page-header"><div><span className="eyebrow">DES REPÈRES DANS LE TEMPS</span><h1>Mon évolution<span className="heading-dot">.</span></h1></div><span className="evolution-header-note">Chaque jour fait partie de ton histoire.</span></header>
    <div className="evolution-intro"><h2>Ton rythme se comprend dans la durée.</h2><p>PsychoSpace observe les changements qui se répètent, pas les mauvais jours.</p></div>
    {state.status === 'loading' && <p className="evolution-message" role="status">PsychoSpace retrace ton évolution…</p>}
    {state.status === 'error' && <div className="evolution-message" role="alert"><p>Je n’arrive pas à retrouver ton évolution pour le moment.</p><button className="primary-button" onClick={() => setAttempt(value => value + 1)}>Réessayer</button></div>}
    {state.status === 'ready' && !state.days.length && <p className="evolution-message">Ton histoire commence avec tes prochains bilans.</p>}
    {state.status === 'ready' && days.length > 0 && <>
      <section className="rhythm-trace" aria-labelledby="trace-title">
        <div className="trace-heading"><div><span className="eyebrow">UNE EMPREINTE DANS LE TEMPS</span><h2 id="trace-title">Trace de rythme</h2></div><label className="period-picker">Période<select aria-label="Période" value={month} onChange={event => { setMonth(event.target.value); setSelection('') }}>{months.map(item => <option key={item} value={item}>{monthLabel(item)}</option>)}</select></label></div>
        <div className="trace-legend">{rhythmMetrics.map(metric => <span key={metric.key}><svg width="30" height="8" aria-hidden="true"><line x1="0" y1="4" x2="30" y2="4" stroke={metric.color} strokeWidth="2" strokeDasharray={metric.dash} /></svg>{metric.label}</span>)}</div>
        <div className="trace-scroll" role="region" aria-label="Trace chronologique, défilement horizontal possible" tabIndex="0">
          <div className="trace-canvas" style={{ width }}>
            <svg width={width} height="345" role="img" aria-labelledby="trace-svg-title trace-svg-description">
              <title id="trace-svg-title">Ton rythme au fil des jours</title>
              <desc id="trace-svg-description">Quatre traces comparent les bilans à la référence personnelle. Au-dessus, une valeur supérieure à l’habitude ; en dessous, une valeur inférieure. Sélectionne un jour avec les boutons pour lire les valeurs originales.</desc>
              <rect x="40" y="171" width={width - 80} height="18" rx="9" fill="#cbd6b807" />
              {missing.length < 4 && <><line x1="40" x2={width - 40} y1="180" y2="180" stroke="#cbd6b84a" strokeDasharray="3 6" /><text x="45" y="161" className="reference-label">Ton rythme habituel</text></>}
              {chosen && <line className="selected-day-line" x1={coordinates.x(chosen.record.timestamp)} x2={coordinates.x(chosen.record.timestamp)} y1="42" y2="310" stroke="#e8ead432" />}
              {rhythmMetrics.map(metric => <g key={metric.key}><path data-metric={metric.key} d={tracePath(days, metric, state.baseline, coordinates)} stroke={metric.color} strokeWidth="2" strokeDasharray={metric.dash} fill="none" strokeLinecap="round" strokeLinejoin="round" />{days.map(day => {
                const value = visualDeviation(day.record[metric.key], state.baseline?.[metric.baseline])
                return value === null ? null : <circle key={day.day} cx={coordinates.x(day.record.timestamp)} cy={coordinates.y(value)} r={chosen?.day === day.day ? 4 : 2} fill={metric.color} />
              })}</g>)}
              {driftVisible && <g className="detection-marker" data-detected-at={drift.detected_at}>
                <line x1={coordinates.x(drift.detected_at)} x2={coordinates.x(drift.detected_at)} y1="33" y2="309" stroke="#d4c1a078" strokeDasharray="2 6" />
                <circle cx={coordinates.x(drift.detected_at)} cy="33" r="4" fill="#d4c1a0" />
                <text x={coordinates.x(drift.detected_at) - 10} y="22" textAnchor="end" className="detection-label">Une évolution remarquée</text>
              </g>}
              <line x1="40" x2={width - 40} y1="311" y2="311" stroke="#ffffff18" />
            </svg>
            <div className="trace-days" aria-label="Choisir un jour">{days.map(day => <button key={day.day} type="button" className={chosen?.day === day.day ? 'selected' : ''} style={{ left: coordinates.x(day.record.timestamp) }} aria-pressed={chosen?.day === day.day} aria-label={`Voir le ${fullDate(day.record.timestamp)}`} onClick={() => setSelection(day.day)}><span>{Number(day.day.slice(-2))}</span><small>{new Intl.DateTimeFormat('fr-FR', { month: 'short', timeZone: 'UTC' }).format(new Date(day.record.timestamp))}</small></button>)}</div>
          </div>
        </div>
        <p className="trace-help">Un repère par jour : le dernier bilan saisi. Les écarts sont ajustés pour réunir les quatre unités ; les valeurs réelles restent ci-dessous. Une journée sans bilan laisse une interruption.</p>
        {missing.length > 0 && <p className="trace-help">Référence absente ou nulle pour {missing.map(metric => metric.label.toLocaleLowerCase('fr')).join(', ')} : les valeurs restent consultables, sans courbe comparative.</p>}
      </section>
      {chosen && <section className="selected-day" aria-labelledby="selected-day-title" aria-live="polite">
        <div className="selected-day-heading"><span className="eyebrow">LES REPÈRES DE CETTE JOURNÉE</span><h2 id="selected-day-title">{fullDate(chosen.record.timestamp)}</h2><p>Un instant de ton histoire, à lire avec tes habitudes.{chosen.count > 1 ? ` ${chosen.count} bilans ce jour ; le dernier est présenté.` : ''}</p></div>
        <dl className="day-values">{rhythmMetrics.map(metric => <div key={metric.key} data-metric={metric.key}><dt>{metric.label}</dt><dd>{metricValue(metric, chosen.record[metric.key])}</dd><p>D’habitude : {metricValue(metric, state.baseline?.[metric.baseline])}</p>{metric.key === 'sleep_hours' && Number.isFinite(chosen.record[metric.key]) && <small>{number(chosen.record[metric.key])} h · repère {number(state.baseline?.[metric.baseline])} h</small>}</div>)}</dl>
      </section>}
      <section className="evolution-reflection"><div className="recent-rhythm"><span className="eyebrow">AU FIL DES DERNIERS BILANS</span><h2>Ce qui se dessine</h2><p>{recentSummary(days, state.baseline)}</p><small>Comparaison descriptive des derniers jours renseignés de la période. Aucune nouvelle détection.</small></div>
        <div className="detection-note"><PsychoSpacePresence state="attentive" /><div>{drift ? <><span className="eyebrow">UN MOMENT REMARQUÉ</span><h2>{fullDate(drift.detected_at)}</h2><p>PsychoSpace a remarqué une évolution à cette date.{!driftVisible && ' Elle se situe en dehors de la période affichée.'}</p><details><summary>Pourquoi PsychoSpace l’a remarqué ?</summary><p>{drift.explanation || 'Aucune explication n’a été enregistrée.'}</p><ul>{(drift.affected_signals || []).map((signal, index) => <li key={signal}>{signalNames[signal] || `Autre repère observé ${index + 1}`}</li>)}</ul><p className="subtle-score">Écart de rythme enregistré : {percent(drift.drift_score)}</p></details></> : <p>Aucun changement n’a encore été enregistré par PsychoSpace.</p>}</div></div>
      </section>
    </>}
  </>
}
