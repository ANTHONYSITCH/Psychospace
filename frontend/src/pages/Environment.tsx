import { useEffect, useState } from 'react'
import { BarChart, Bar, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getSensors } from '../api/client'
import type { SensorMeasurement } from '../types/checkin'

export function EnvironmentPage() {
  const [sensors, setSensors] = useState<SensorMeasurement[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const response = await getSensors()
        setSensors(response.data)
      } catch {
        setSensors([])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const chartData = sensors.map((sensor) => ({
    name: sensor.sensor_name,
    value: sensor.latest_value ?? 0,
    unit: sensor.unit ?? ''
  }))

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Sensors</p>
        <h1 className="text-3xl font-semibold text-white">Environnement</h1>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-8 text-slate-300">Chargement des capteurs...</div>
      ) : !chartData.length ? (
        <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-8 text-slate-300">
          Aucune donnée de capteur disponible pour le moment.
        </div>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
            <div className="mb-4 text-lg font-medium text-white">Mesures des capteurs</div>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip formatter={(value: number) => [`${value}`, 'Valeur']} />
                  <Bar dataKey="value" fill="#38bdf8" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="space-y-4">
            {sensors.map((sensor) => (
              <div key={sensor.id} className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-cyan-300">{sensor.sensor_type}</div>
                <div className="mt-2 flex items-baseline justify-between">
                  <span className="text-2xl font-semibold text-white">{sensor.latest_value ?? '—'}</span>
                  <span className="text-sm text-slate-400">{sensor.unit ?? ''}</span>
                </div>
                <div className="mt-3 text-sm text-slate-300">{sensor.sensor_name}</div>
                <div className="mt-1 text-xs text-slate-400">{sensor.location ?? 'Emplacement non renseigné'}</div>
                <div className="mt-3 text-xs text-emerald-300">{sensor.quality_status ?? 'qualité inconnue'}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
