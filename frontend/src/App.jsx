import { useEffect, useRef, useState } from 'react'
import Icon from './components/Icon'
import Overview from './components/Overview'
import DailyCheckin from './components/DailyCheckin'
import Companion from './components/Companion'
import Evolution from './components/Evolution'
import Memory from './components/Memory'
import PsychoSpacePresence from './components/PsychoSpacePresence'

const spaces = ['Overview', 'Pulse', 'Companion', 'Evolution', 'Memory', 'Care']
const labels = { Overview: "Vue d'ensemble", Pulse: 'État du jour', Companion: 'Compagnon', Evolution: 'Mon évolution', Memory: 'Mémoire', Care: 'Accompagnement' }
function selectedPage() { return spaces.find(page => `#${page.toLowerCase()}` === window.location.hash) || 'Overview' }

export default function App() {
  const [page, setPage] = useState(selectedPage)
  const main = useRef(null)
  useEffect(() => {
    const onHash = () => { setPage(selectedPage()); main.current?.focus() }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  return <div className="app-shell">
    <a href="#main" className="skip-link" onClick={event => { event.preventDefault(); main.current?.focus() }}>Aller au contenu</a>
    <aside className="sidebar">
      <a className="brand" href="#overview" aria-label="PsychoSpace, vue d'ensemble"><span className="brand-symbol" aria-hidden="true">✳</span><span>psycho<span className="brand-light">space</span><small>UN ESPACE POUR SOI</small></span></a>
      <div className="nav-heading eyebrow">À BORD</div>
      <nav aria-label="Navigation principale">{spaces.map((space, index) => <a key={space} aria-label={labels[space]} href={`#${space.toLowerCase()}`} className={page === space ? 'nav-link active' : 'nav-link'} aria-current={page === space ? 'page' : undefined}><Icon name={space.toLowerCase()} /><span>{labels[space]}</span>{page === space ? <span className="nav-dot" /> : <span className="nav-number">0{index + 1}</span>}</a>)}</nav>
      <div className="sidebar-bottom"><div className="quiet-mark" aria-hidden="true"><span /><span /><span /></div><p>Un peu plus près<br />de ton propre rythme.</p><div className="local-note"><span /> TOUT RESTE À BORD</div></div>
    </aside>
    <main id="main" ref={main} tabIndex="-1" className="main-content" key={page}>
      {page === 'Overview' ? <Overview /> : page === 'Pulse' ? <DailyCheckin /> : page === 'Companion' ? <Companion /> : page === 'Evolution' ? <Evolution /> : page === 'Memory' ? <Memory /> : <><header className="page-header"><div><span className="eyebrow">TON ESPACE PERSONNEL</span><h1>{labels[page]}<span className="heading-dot">.</span></h1></div><span className="phase-tag">À VENIR</span></header><section className="placeholder"><PsychoSpacePresence /><span className="eyebrow">UN ESPACE PREND FORME</span><h2>La suite se prépare doucement.</h2><p>Cet espace n’est pas encore disponible.<br />En attendant, retrouve ta vue d’ensemble.</p><a href="#overview" className="primary-button">Retour à la vue d’ensemble <Icon name="arrow" /></a></section></>}
    </main>
  </div>
}
