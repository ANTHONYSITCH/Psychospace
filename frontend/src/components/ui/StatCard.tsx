import type { ReactNode } from 'react'

type StatCardProps = {
  title: string
  value: string
  hint?: string
  accent?: 'blue' | 'cyan' | 'green' | 'amber' | 'rose'
  icon?: ReactNode
}

const accentMap = {
  blue: 'border-blue-500/30 bg-blue-500/10 text-blue-200',
  cyan: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-200',
  green: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
  amber: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
  rose: 'border-rose-500/30 bg-rose-500/10 text-rose-200'
}

export function StatCard({ title, value, hint, accent = 'blue', icon }: StatCardProps) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-lg shadow-slate-950/30">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm text-slate-400">{title}</p>
        {icon && <div className={`rounded-lg border p-2 ${accentMap[accent]}`}>{icon}</div>}
      </div>
      <div className="text-2xl font-semibold text-white">{value}</div>
      {hint && <div className="mt-2 text-xs text-slate-400">{hint}</div>}
    </div>
  )
}
