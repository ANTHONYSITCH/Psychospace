import { useEffect, useRef, useState } from 'react'
import { loadProfile, submitCheckin } from '../api'
import { answerLabel, steps, validAnswer } from '../checkin'
import PsychoSpacePresence from './PsychoSpacePresence'
import Icon from './Icon'
import './DailyCheckin.css'

export default function DailyCheckin() {
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState({})
  const [name, setName] = useState('')
  const [status, setStatus] = useState('editing')
  const saving = useRef(false)
  const heading = useRef(null)
  const step = steps[index], value = answers[step.key]
  const valid = validAnswer(step, value)
  const pending = status === 'saving'
  useEffect(() => {
    const controller = new AbortController()
    loadProfile(controller.signal).then(profile => setName(profile?.first_name || '')).catch(() => {})
    return () => controller.abort()
  }, [])
  useEffect(() => { heading.current?.focus() }, [index, status === 'success'])
  function change(value) {
    setAnswers(current => ({ ...current, [step.key]: value }))
    setStatus('editing')
  }
  async function next(event) {
    event.preventDefault()
    if (saving.current || !valid) return
    if (index < steps.length - 1) { setIndex(index + 1); setStatus('editing'); return }
    if (!steps.every(item => validAnswer(item, answers[item.key]))) return
    saving.current = true
    setStatus('saving')
    try { await submitCheckin(answers); setStatus('success') }
    catch { setStatus('error') }
    finally { saving.current = false }
  }
  return <>
    <header className="page-header"><div><span className="eyebrow">UN MOMENT POUR TOI</span><h1>État du jour<span className="heading-dot">.</span></h1></div><span className="checkin-header-note">À ton rythme, sans jugement.</span></header>
    <section className="checkin-space" aria-label="Ton état du jour">
      <PsychoSpacePresence state={status === 'success' ? 'idle' : 'attentive'} />
      {status === 'success' ? <div className="checkin-success">
        <span className="eyebrow">TES REPÈRES SONT ENREGISTRÉS</span>
        <h2 ref={heading} tabIndex="-1">Merci{name ? ` ${name}` : ''}.</h2>
        <p role="status">Ton état du jour a bien été enregistré.</p>
        <dl className="checkin-summary">{steps.filter(item => ['sleep_hours', 'energy', 'fatigue', 'activity_minutes'].includes(item.key)).map(item => <div key={item.key}><dt>{item.label}</dt><dd>{answerLabel(item, answers[item.key])}</dd></div>)}</dl>
        <a href="#overview" className="primary-button">Retour à la vue d’ensemble <Icon name="arrow" /></a>
      </div> : <>
        <div className="checkin-progress" role="progressbar" aria-label="Progression de ton état du jour" aria-valuemin={0} aria-valuemax={7} aria-valuenow={index} aria-valuetext={`${index} étapes parcourues sur 7`}>
          {steps.map((item, position) => <span key={item.key} className={position < index ? 'done' : position === index ? 'current' : ''} />)}
        </div>
        <form onSubmit={next} className="checkin-form" aria-busy={pending}>
          <span className="eyebrow">{step.label}</span>
          <h2 ref={heading} tabIndex="-1" id="checkin-question">{step.question}</h2>
          <p id="checkin-hint" className="checkin-hint">{step.hint}</p>
          <fieldset disabled={pending} aria-labelledby="checkin-question" aria-describedby="checkin-hint">
            {step.unit ? <>
              <label className="duration-label" htmlFor={step.key}>{step.key === 'sleep_hours' ? 'Durée en heures' : 'Durée en minutes'}</label>
              <div className="duration-input"><input id={step.key} type="number" inputMode="decimal" min="0" max={step.max} step={step.increment} value={value ?? ''} onChange={event => change(event.target.value === '' ? undefined : event.target.valueAsNumber)} aria-describedby="duration-help" /><span>{step.unit}</span></div>
              <p id="duration-help" className="duration-help">{step.key === 'sleep_hours' ? 'Par demi-heures, de 0 à 24 h. Par exemple : 6,5 pour 6 h 30.' : 'De 0 à 1 440 min. Choisis un repère ou saisis ta durée exacte.'}</p>
              <div className="duration-presets" aria-label="Quelques repères">{step.choices.map(choice => <button type="button" key={choice} aria-pressed={value === choice} onClick={() => change(choice)}>{answerLabel(step, choice)}</button>)}</div>
            </> : <>
              <div className="checkin-scale">{Array.from({ length: 10 }, (_, position) => position + 1).map(score => <label key={score}><input type="radio" name={step.key} value={score} checked={value === score} onChange={() => change(score)} aria-label={`${score} sur 10`} /><span>{score}</span></label>)}</div>
              <div className="scale-labels"><span>{step.low}</span><span>{step.high}</span></div>
            </>}
            <output className="checkin-answer" aria-live="polite">{answerLabel(step, value)}</output>
          </fieldset>
          {status === 'error' && <p className="checkin-error" role="alert">Je n’ai pas réussi à enregistrer ton état pour le moment. Tes réponses sont conservées.</p>}
          <div className="checkin-actions"><button className="back-button" type="button" disabled={index === 0 || pending} onClick={() => { setIndex(index - 1); setStatus('editing') }}>Retour</button>
            <button className="primary-button" type="submit" disabled={!valid || pending}>{pending ? 'J’enregistre ton état…' : status === 'error' ? 'Réessayer' : index === steps.length - 1 ? 'Enregistrer mon état' : 'Continuer'}{!pending && <Icon name="arrow" />}</button>
          </div>
          {pending && <span role="status" className="checkin-saving">J’enregistre ton état…</span>}
        </form>
      </>}
      <p className="checkin-footnote"><Icon name="lock" /> Tes réponses restent à bord.</p>
    </section>
  </>
}
