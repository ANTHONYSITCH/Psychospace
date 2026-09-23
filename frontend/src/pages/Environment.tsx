export function EnvironmentPage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Sensors</p>
        <h1 className="text-3xl font-semibold text-white">Environnement</h1>
      </div>

      <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-8 text-slate-300">
        Aucune donnée de capteur disponible pour le moment. Le frontend affichera automatiquement les mesures quand elles seront exposées par FastAPI.
      </div>
    </div>
  )
}
