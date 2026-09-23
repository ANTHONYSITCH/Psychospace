export function ProfilePage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Astronaut profile</p>
        <h1 className="text-3xl font-semibold text-white">Profil</h1>
      </div>

      <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-8 text-slate-300">
        Aucune donnée d’astronaute disponible pour le moment. Les informations seront affichées quand FastAPI les exposera.
      </div>
    </div>
  )
}
