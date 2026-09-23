import { useEffect, useMemo, useState } from 'react'
import { Activity, HeartPulse, MoonStar, ShieldAlert, Sparkles } from 'lucide-react'
import { getHealth } from '../api/client'
import { getCheckins } from '../api/checkins'
import { StatCard } from '../components/ui/StatCard'
import type { Checkin } from '../types/checkin'

export function DashboardPage() {
  const [checkins, setCheckins] = useState<Checkin[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [apiConnected, setApiConnected] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        await getHealth()
        setApiConnected(true)
      } catch {
        setApiConnected(false)
      }

      try {
        const response = await getCheckins()
        setCheckins(response.data)
      } catch {
        setError('Impossible de contacter le serveur. Vérifiez que FastAPI fonctionne sur localhost:8000.')
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  const latest = useMemo(() => {
    if (!checkins.length) return null
    return [...checkins].sort((a, b) => new Date(b.checkin_date).getTime() - new Date(a.checkin_date).getTime())[0]
  }, [checkins])

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Mission overview</p>
          <h1 className="text-3xl font-semibold text-white">SPACEWELL Dashboard</h1>
        </div>
        <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm ${apiConnected ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200' : 'border-rose-500/30 bg-rose-500/10 text-rose-200'}`}>
          <span className={`h-2.5 w-2.5 rounded-full ${apiConnected ? 'bg-emerald-400' : 'bg-rose-400'}`} />
          {apiConnected ? 'API Connected' : 'API Offline'}
        </div>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-8 text-slate-300">Chargement des données...</div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-200">{error}</div>
      ) : !checkins.length ? (
        <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-8 text-slate-300">Aucune donnée disponible pour le moment.</div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard title="Dernier état" value={String(latest?.overall_state ?? '—')} hint="État global" accent="blue" icon={<HeartPulse className="h-4 w-4" />} />
            <StatCard title="Sommeil" value={latest?.sleep_duration_hours ? `${latest.sleep_duration_hours} h` : '—'} hint="Durée moyenne" accent="cyan" icon={<MoonStar className="h-4 w-4" />} />
            <StatCard title="Fatigue" value={String(latest?.fatigue ?? '—')} hint="Score sur 10" accent="amber" icon={<ShieldAlert className="h-4 w-4" />} />
            <StatCard title="Énergie" value={String(latest?.energy ?? '—')} hint="Score sur 10" accent="green" icon={<Sparkles className="h-4 w-4" />} />
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.4fr,0.8fr]">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-medium text-white">Dernier questionnaire</h2>
                <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-1 text-xs text-cyan-200">{latest?.checkin_date ?? '—'}</span>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <div className="text-xs uppercase text-slate-400">Stress</div>
                  <div className="mt-1 text-2xl font-semibold text-white">{latest?.stress ?? '—'}</div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <div className="text-xs uppercase text-slate-400">Motivation</div>
                  <div className="mt-1 text-2xl font-semibold text-white">{latest?.motivation ?? '—'}</div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <div className="text-xs uppercase text-slate-400">Concentration</div>
                  <div className="mt-1 text-2xl font-semibold text-white">{latest?.concentration ?? '—'}</div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <div className="text-xs uppercase text-slate-400">Moral</div>
                  <div className="mt-1 text-2xl font-semibold text-white">{latest?.mood ?? '—'}</div>
                </div>
              </div>
              {latest?.comment && <p className="mt-4 text-sm text-slate-300">{latest.comment}</p>}
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <h2 className="mb-4 text-lg font-medium text-white">Context mission</h2>
              <div className="space-y-3 text-sm text-slate-300">
                <div className="flex justify-between border-b border-slate-800 pb-2"><span>Astronaute</span><span className="text-white">#{latest?.astronaut_id ?? '—'}</span></div>
                <div className="flex justify-between border-b border-slate-800 pb-2"><span>Dernier check-in</span><span className="text-white">{latest?.checkin_date ?? '—'}</span></div>
                <div className="flex justify-between border-b border-slate-800 pb-2"><span>Source stress</span><span className="text-white">{latest?.stress_source ?? '—'}</span></div>
                <div className="flex justify-between"><span>Évolution</span><span className="text-white">{latest?.compared_to_yesterday ?? '—'}</span></div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
