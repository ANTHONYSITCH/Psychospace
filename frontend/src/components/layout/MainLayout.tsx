import { Activity, BarChart3, BrainCircuit, LayoutDashboard, MoonStar, ShieldCheck, UserCircle } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/questionnaire', label: 'Questionnaire', icon: MoonStar },
  { to: '/history', label: 'Historique', icon: BarChart3 },
  { to: '/environment', label: 'Environnement', icon: Activity },
  { to: '/ai-analysis', label: 'Analyse IA', icon: BrainCircuit },
  { to: '/profile', label: 'Profil', icon: UserCircle }
]

export function MainLayout() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex max-w-[1600px] gap-6 px-4 py-6 lg:px-6">
        <aside className="hidden w-72 flex-col rounded-3xl border border-slate-800 bg-slate-900/80 p-5 shadow-2xl shadow-slate-950/50 lg:flex">
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-cyan-500/20 text-cyan-300 ring-1 ring-cyan-400/30">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.28em] text-slate-400">Mission</div>
              <div className="text-xl font-semibold text-white">SPACEWELL</div>
            </div>
          </div>

          <nav className="space-y-2">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                    isActive
                      ? 'border border-cyan-500/30 bg-cyan-500/10 text-cyan-100'
                      : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                  }`
                }
              >
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ))}
          </nav>
        </aside>

        <main className="flex-1 rounded-3xl border border-slate-800 bg-slate-900/60 p-4 shadow-2xl shadow-slate-950/40 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
