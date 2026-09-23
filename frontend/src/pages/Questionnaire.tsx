import { useState } from 'react'
import { createCheckin } from '../api/checkins'

const sleepOptions = ['< 5 h', '5–6 h', '6–7 h', '7–8 h', '> 8 h']
const sourceOptions = ['Aucune', 'Travail / charge de travail', 'Expérience scientifique', 'Problème technique', 'Communication', 'Isolement', 'Sommeil / fatigue', 'Environnement', 'Autre']
const difficultyOptions = ['Non', 'Fatigue inhabituelle', 'Difficulté à dormir', 'Difficulté à me concentrer', 'Stress inhabituel', 'Baisse de moral', 'Autre']
const compareOptions = ['Beaucoup mieux', 'Mieux', 'Similaire', 'Moins bien', 'Beaucoup moins bien']

export function QuestionnairePage() {
  const [form, setForm] = useState({
    astronaut_id: 1,
    checkin_date: new Date().toISOString().slice(0, 10),
    sleep_duration_hours: 7.5,
    sleep_quality: 8,
    fatigue: 3,
    energy: 8,
    stress: 4,
    stress_source: 'Aucune',
    mood: 8,
    motivation: 9,
    concentration: 8,
    unusual_difficulty: 'Non',
    overall_state: 8,
    compared_to_yesterday: 'Similaire',
    comment: ''
  })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const handleChange = (field: string, value: string | number) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setMessage('')
    setError('')

    try {
      await createCheckin({
        ...form,
        stress_source: form.stress_source || null,
        unusual_difficulty: form.unusual_difficulty || null,
        compared_to_yesterday: form.compared_to_yesterday || null,
        comment: form.comment || null
      })
      setMessage('Questionnaire enregistré avec succès.')
    } catch (err) {
      setError('Impossible d’enregistrer le questionnaire. Vérifiez le serveur FastAPI.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Daily check-in</p>
        <h1 className="text-3xl font-semibold text-white">Questionnaire</h1>
      </div>

      <form onSubmit={handleSubmit} className="grid gap-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <label className="space-y-2 text-sm text-slate-300">
            <span>Date</span>
            <input type="date" value={form.checkin_date} onChange={(e) => handleChange('checkin_date', e.target.value)} className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-white" />
          </label>

          <label className="space-y-2 text-sm text-slate-300">
            <span>Astronaute ID</span>
            <input type="number" min={1} value={form.astronaut_id} onChange={(e) => handleChange('astronaut_id', Number(e.target.value))} className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-white" />
          </label>

          <label className="space-y-2 text-sm text-slate-300">
            <span>Durée du sommeil</span>
            <input type="number" step="0.1" value={form.sleep_duration_hours} onChange={(e) => handleChange('sleep_duration_hours', Number(e.target.value))} className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-white" />
          </label>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <label className="space-y-2 text-sm text-slate-300">
            <span>Qualité du sommeil (0-10)</span>
            <input type="range" min={0} max={10} value={form.sleep_quality} onChange={(e) => handleChange('sleep_quality', Number(e.target.value))} className="w-full accent-cyan-400" />
            <div className="text-cyan-200">{form.sleep_quality}</div>
          </label>

          <label className="space-y-2 text-sm text-slate-300">
            <span>Fatigue (0-10)</span>
            <input type="range" min={0} max={10} value={form.fatigue} onChange={(e) => handleChange('fatigue', Number(e.target.value))} className="w-full accent-amber-400" />
            <div className="text-amber-200">{form.fatigue}</div>
          </label>

          <label className="space-y-2 text-sm text-slate-300">
            <span>Énergie (0-10)</span>
            <input type="range" min={0} max={10} value={form.energy} onChange={(e) => handleChange('energy', Number(e.target.value))} className="w-full accent-emerald-400" />
            <div className="text-emerald-200">{form.energy}</div>
          </label>

          <label className="space-y-2 text-sm text-slate-300">
            <span>Stress (0-10)</span>
            <input type="range" min={0} max={10} value={form.stress} onChange={(e) => handleChange('stress', Number(e.target.value))} className="w-full accent-rose-400" />
            <div className="text-rose-200">{form.stress}</div>
          </label>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <label className="space-y-2 text-sm text-slate-300">
            <span>Source de stress</span>
            <select value={form.stress_source} onChange={(e) => handleChange('stress_source', e.target.value)} className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-white">
              {sourceOptions.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>

          <label className="space-y-2 text-sm text-slate-300">
            <span>Moral (0-10)</span>
            <input type="range" min={0} max={10} value={form.mood} onChange={(e) => handleChange('mood', Number(e.target.value))} className="w-full accent-violet-400" />
            <div className="text-violet-200">{form.mood}</div>
          </label>

          <label className="space-y-2 text-sm text-slate-300">
            <span>Motivation (0-10)</span>
            <input type="range" min={0} max={10} value={form.motivation} onChange={(e) => handleChange('motivation', Number(e.target.value))} className="w-full accent-cyan-400" />
            <div className="text-cyan-200">{form.motivation}</div>
          </label>

          <label className="space-y-2 text-sm text-slate-300">
            <span>Concentration (0-10)</span>
            <input type="range" min={0} max={10} value={form.concentration} onChange={(e) => handleChange('concentration', Number(e.target.value))} className="w-full accent-blue-400" />
            <div className="text-blue-200">{form.concentration}</div>
          </label>

          <label className="space-y-2 text-sm text-slate-300">
            <span>Difficulté inhabituelle</span>
            <select value={form.unusual_difficulty} onChange={(e) => handleChange('unusual_difficulty', e.target.value)} className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-white">
              {difficultyOptions.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>

          <label className="space-y-2 text-sm text-slate-300">
            <span>État général (0-10)</span>
            <input type="range" min={0} max={10} value={form.overall_state} onChange={(e) => handleChange('overall_state', Number(e.target.value))} className="w-full accent-cyan-400" />
            <div className="text-cyan-200">{form.overall_state}</div>
          </label>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2 text-sm text-slate-300">
            <span>Comparaison avec hier</span>
            <select value={form.compared_to_yesterday} onChange={(e) => handleChange('compared_to_yesterday', e.target.value)} className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-white">
              {compareOptions.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>

          <label className="space-y-2 text-sm text-slate-300">
            <span>Commentaire</span>
            <textarea value={form.comment} onChange={(e) => handleChange('comment', e.target.value)} rows={4} placeholder="Décrivez le ressenti du jour..." className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-white" />
          </label>
        </div>

        {message && <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">{message}</div>}
        {error && <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>}

        <button type="submit" disabled={loading} className="w-full rounded-xl bg-cyan-500 px-4 py-3 font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-70">
          {loading ? 'Enregistrement...' : 'Enregistrer le questionnaire'}
        </button>
      </form>
    </div>
  )
}
