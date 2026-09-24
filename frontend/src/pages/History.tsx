import { useEffect, useMemo, useState } from 'react'
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getCheckins } from '../api/checkins'
import { getSensors } from '../api/client'
import type { Checkin, SensorMeasurement } from '../types/checkin'

export function HistoryPage() {
  const [checkins, setCheckins] = useState<Checkin[]>([])
  const [sensors, setSensors] = useState<SensorMeasurement[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [checkinsResponse, sensorsResponse] = await Promise.all([getCheckins(), getSensors()])
        setCheckins(checkinsResponse.data)
        setSensors(sensorsResponse.data)
      } catch {
        setCheckins([])
        setSensors([])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const chartData = useMemo(
    () =>
      [...checkins]
        .sort((a, b) => new Date(a.checkin_date).getTime() - new Date(b.checkin_date).getTime())
        .map((item) => ({
          date: item.checkin_date,
          sleep: item.sleep_duration_hours ?? 0,
          fatigue: item.fatigue ?? 0,
          energy: item.energy ?? 0,
          stress: item.stress ?? 0,
          mood: item.mood ?? 0,
          motivation: item.motivation ?? 0,
          concentration: item.concentration ?? 0,
          overall: item.overall_state ?? 0,
        })),
    [checkins],
  )

  const sensorData = useMemo(
    () =>
      sensors.map((sensor) => ({
        name: sensor.sensor_name,
        value: sensor.latest_value ?? 0,
        unit: sensor.unit ?? '',
      })),
    [sensors],
  )

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
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
            <div className="mb-4 text-lg font-medium text-white">Tendances psychophysiologiques</div>
            <div className="h-[320px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="date" stroke="#94a3b8" />
                  <YAxis domain={[0, 10]} stroke="#94a3b8" />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="stress" fill="#f87171" barSize={10} />
                  <Line type="monotone" dataKey="energy" stroke="#34d399" strokeWidth={2} dot={{ r: 2 }} />
                  <Line type="monotone" dataKey="fatigue" stroke="#f59e0b" strokeWidth={2} dot={{ r: 2 }} />
                  <Line type="monotone" dataKey="overall" stroke="#22d3ee" strokeWidth={2} dot={{ r: 2 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
            <div className="mb-4 text-lg font-medium text-white">Capteurs et signaux environnementaux</div>
            <div className="h-[260px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={sensorData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip formatter={(value: number) => [`${value}`, 'Valeur']} />
                  <Bar dataKey="value" fill="#8b5cf6" barSize={30} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
