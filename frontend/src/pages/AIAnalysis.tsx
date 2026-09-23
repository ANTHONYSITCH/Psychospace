export function AIAnalysisPage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Future integration</p>
        <h1 className="text-3xl font-semibold text-white">Analyse IA</h1>
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <div className="text-sm text-slate-400">Résumé</div>
          <div className="mt-3 text-slate-300">Aucun résumé disponible pour le moment.</div>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <div className="text-sm text-slate-400">Tendances</div>
          <div className="mt-3 text-slate-300">Les tendances seront affichées quand l’analyse sera disponible.</div>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <div className="text-sm text-slate-400">Points d’attention</div>
          <div className="mt-3 text-slate-300">Préparation de l’architecture IA côté backend et frontend.</div>
        </div>
      </div>
    </div>
  )
}
