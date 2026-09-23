/** Reusable visual presence. States: idle, thinking, attentive, drift. No business logic. */
export default function PsychoSpacePresence({ state = 'idle', level = 'low' }) {
  return <div className={`presence presence--${state} presence--${level}`} aria-hidden="true">
    <div className="presence-glow" />
    <div className="orbit orbit-one" /><div className="orbit orbit-two" />
    {state === 'drift' && <div className="orbit orbit-three" />}
    <div className="presence-body"><div className="presence-inner" /><div className="presence-core" /></div>
    <span className="orb-point" />
  </div>
}
