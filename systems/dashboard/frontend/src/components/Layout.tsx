import { NavLink, Outlet } from 'react-router-dom'
import {
  Users, MessageSquare, GitBranch, BarChart2,
  FileText, Activity
} from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { to: '/leads', icon: Users, label: 'Лиды' },
  { to: '/dialogs', icon: MessageSquare, label: 'Диалоги' },
  { to: '/pipeline', icon: GitBranch, label: 'Pipeline' },
  { to: '/analytics', icon: BarChart2, label: 'Аналитика' },
  { to: '/prompts', icon: FileText, label: 'Промпты' },
]

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 bg-card border-r border-border flex flex-col shrink-0">
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-accent" />
            <span className="font-semibold text-sm">Harmonic Trifid</span>
          </div>
          <p className="text-xs text-muted mt-0.5">Dashboard v2</p>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-accent/20 text-accent'
                    : 'text-muted hover:text-white hover:bg-white/5'
                )
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-border">
          <a
            href="http://localhost:8001/docs"
            target="_blank"
            rel="noreferrer"
            className="text-xs text-muted hover:text-white transition-colors"
          >
            API Docs →
          </a>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto bg-surface">
        <Outlet />
      </main>
    </div>
  )
}
