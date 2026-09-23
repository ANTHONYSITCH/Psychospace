import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { getCheckins } from '../api/checkins'
import type { Checkin } from '../types/checkin'

export function HistoryPage() {
  const [checkins, setCheckins] = useState<Checkin[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const response = await getCheckins()
        setCheckins(response.data)
      } catch {
        setCheckins([])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const chartData = [...checkins].sort((a, b) => new Date(a.checkin_date).getTime() - new Date(b.checkin_date).getTime()).map((item) => ({
    date: item.checkin_date,
    sleep: item.sleep_duration_hours ?? 0,
    fatigue: item.fatigue ?? 0,
    energy: item.energy ?? 0,
    stress: item.stress ?? 0,
    mood: item.mood ?? 0,
    motivation: item.motivation ?? 0,
    concentration: item.concentration ?? 0,
    overall: item.overall_state ?? 0
  }))

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Historical trend</p>
        <h1 className="text-3xl font-semibold text-white">Historique</h1>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-8 text-slate-300">Chargement des données...</div>
      ) : !chartData.length ? (
        <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-8 text-slate-300">Aucune donnée disponible pour le moment.</div>
      ) : (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
          <div className="mb-4 text-lg font-medium text-white">Tendances psychophysiologiques</div>
          <div className="h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" />
                <YAxis domain={[0, 10]} stroke="#94a3b8" />
                <Tooltip />
                <Line type="monotone" dataKey="fatigue" stroke="#f59e0b" strokeWidth={2} dot={{ r: 2 }} />
                <Line type="monotone" dataKey="energy" stroke="#34d399" strokeWidth={2} dot={{ r: 2 }} />
                <Line type="monotone" dataKey="stress" stroke="#f87171" strokeWidth={2} dot={{ r: 2 }} />
                <Line type="monotone" dataKey="overall" stroke="#22d3ee" strokeWidth={2} dot={{ r: 2 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}
