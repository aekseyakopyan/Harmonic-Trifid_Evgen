import { useState, useCallback, useEffect, useRef } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  Users, MessageSquare, GitBranch, BarChart2,
  FileText, Activity, Home, Menu, X, Bell, Filter, BookOpen, Briefcase
} from 'lucide-react'
import clsx from 'clsx'
import { useWebSocket } from '../hooks/useWebSocket'

const navItems = [
  { to: '/', icon: Home, label: 'Обзор', exact: true },
  { to: '/leads', icon: Users, label: 'Лиды' },
  { to: '/dialogs', icon: MessageSquare, label: 'Диалоги' },
  { to: '/pipeline', icon: GitBranch, label: 'Pipeline' },
  { to: '/analytics', icon: BarChart2, label: 'Аналитика' },
  { to: '/filter-stats', icon: Filter, label: 'Фильтр' },
  { to: '/prompts', icon: FileText, label: 'Промпты' },
  { to: '/vacancies', icon: Briefcase, label: 'Вакансии' },
  { to: '/guide', icon: BookOpen, label: 'Инструкция' },
]

interface Toast {
  id: number
  title: string
  body: string
  type: 'hot' | 'info'
}

function MoscowClock() {
  const [time, setTime] = useState(() => {
    return new Date().toLocaleTimeString('ru-RU', { timeZone: 'Europe/Moscow', hour: '2-digit', minute: '2-digit', second: '2-digit' })
  })
  useEffect(() => {
    const id = setInterval(() => {
      setTime(new Date().toLocaleTimeString('ru-RU', { timeZone: 'Europe/Moscow', hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    }, 1000)
    return () => clearInterval(id)
  }, [])
  return (
    <div className="px-3 py-2 border-t border-border">
      <div className="text-xs text-muted">Москва</div>
      <div className="font-mono text-sm text-white/80 tracking-wider">{time}</div>
    </div>
  )
}

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [toasts, setToasts] = useState<Toast[]>([])
  const toastIdRef = useRef(0)

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = ++toastIdRef.current
    setToasts(prev => [...prev.slice(-4), { ...toast, id }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 5000)
  }, [])

  useWebSocket('leads', useCallback((event: unknown) => {
    const ev = event as { event?: string; tier?: string; full_name?: string; id?: number }
    if (ev.event === 'lead_updated' && ev.tier === 'HOT') {
      addToast({ title: '🔥 HOT лид!', body: ev.full_name ? `${ev.full_name}` : `Lead #${ev.id}`, type: 'hot' })
    } else if (ev.event === 'new_hot_lead') {
      addToast({ title: '🔥 Новый HOT лид!', body: ev.full_name || `Lead #${ev.id}`, type: 'hot' })
    }
  }, [addToast]))

  // Close sidebar on route change for mobile
  useEffect(() => {
    setSidebarOpen(false)
  }, [])

  const Sidebar = () => (
    <aside className={clsx(
      'w-56 bg-card border-r border-border flex flex-col shrink-0',
      // Mobile: fixed overlay
      'max-md:fixed max-md:inset-y-0 max-md:left-0 max-md:z-50 max-md:shadow-2xl max-md:transition-transform max-md:duration-200',
      sidebarOpen ? 'max-md:translate-x-0' : 'max-md:-translate-x-full'
    )}>
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-accent" />
          <div>
            <span className="font-semibold text-sm">Harmonic Trifid</span>
            <p className="text-xs text-muted">Dashboard v2</p>
          </div>
        </div>
        <button className="md:hidden text-muted hover:text-white" onClick={() => setSidebarOpen(false)}>
          <X className="w-4 h-4" />
        </button>
      </div>
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map(({ to, icon: Icon, label, exact }) => (
          <NavLink
            key={to}
            to={to}
            end={exact}
            onClick={() => setSidebarOpen(false)}
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
      <MoscowClock />
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
  )

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Mobile overlay backdrop */}
      {sidebarOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/50"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <Sidebar />

      {/* Main */}
      <main className="flex-1 overflow-auto bg-surface flex flex-col min-w-0">
        {/* Mobile topbar */}
        <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-border bg-card shrink-0">
          <button onClick={() => setSidebarOpen(true)} className="text-muted hover:text-white">
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-accent" />
            <span className="font-semibold text-sm">Harmonic Trifid</span>
          </div>
        </div>
        <div className="flex-1 overflow-auto">
          <Outlet />
        </div>
      </main>

      {/* HOT Notification toasts */}
      <div className="fixed bottom-4 right-4 z-[100] space-y-2 pointer-events-none">
        {toasts.map(toast => (
          <div
            key={toast.id}
            className={clsx(
              'pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-xl shadow-lg border min-w-[240px] max-w-sm',
              'animate-slide-in-right',
              toast.type === 'hot'
                ? 'bg-red-950/90 border-red-500/40 text-white'
                : 'bg-card border-border text-white'
            )}
          >
            <Bell className={clsx('w-4 h-4 mt-0.5 shrink-0', toast.type === 'hot' ? 'text-red-400' : 'text-accent')} />
            <div className="flex-1">
              <p className="text-sm font-medium">{toast.title}</p>
              <p className="text-xs text-white/70 mt-0.5">{toast.body}</p>
            </div>
            <button
              className="text-white/50 hover:text-white shrink-0"
              onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
