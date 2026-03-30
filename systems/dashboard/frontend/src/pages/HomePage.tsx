import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { analyticsApi } from '../api/client'
import { Users, MessageSquare, TrendingUp, Flame, Thermometer, Snowflake, CheckCircle, Clock } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

const TIER_COLORS = { HOT: '#ef4444', WARM: '#f59e0b', COLD: '#3b82f6', null: '#4b5563' }

function StatCard({
  icon: Icon, label, value, sub, color = 'text-white',
}: {
  icon: React.ElementType; label: string; value: string | number; sub?: string; color?: string
}) {
  return (
    <div className="card flex items-center gap-4">
      <div className="p-3 rounded-xl bg-white/5">
        <Icon className={`w-5 h-5 ${color}`} />
      </div>
      <div>
        <p className="text-xs text-muted">{label}</p>
        <p className={`text-2xl font-bold ${color}`}>{value}</p>
        {sub && <p className="text-xs text-muted">{sub}</p>}
      </div>
    </div>
  )
}

export default function HomePage() {
  const { data: stats } = useQuery({
    queryKey: ['home-stats'],
    queryFn: () => analyticsApi.home().then(r => r.data),
    refetchInterval: 30000,
  })

  const { data: funnel } = useQuery({
    queryKey: ['funnel'],
    queryFn: () => analyticsApi.funnel().then(r => r.data),
  })

  const tierData = funnel?.by_tier ?? []
  const statusData = funnel?.by_status ?? []

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Обзор</h1>
          <p className="text-sm text-muted mt-0.5">Harmonic Trifid — система автоматического аутрича</p>
        </div>
        <div className="text-xs text-muted">
          {new Date().toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard icon={Users} label="Всего лидов" value={stats?.total ?? '—'} sub={`+${stats?.new_today ?? 0} сегодня`} />
        <StatCard icon={Flame} label="HOT лиды" value={stats?.hot ?? '—'} color="text-red-400" />
        <StatCard icon={MessageSquare} label="Активных диалогов" value={stats?.dialogs_active ?? '—'} color="text-blue-400" />
        <StatCard icon={CheckCircle} label="Квалифицированных" value={stats?.qualified ?? '—'} sub={`${stats?.conversion_rate ?? 0}% конверсия`} color="text-green-400" />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard icon={Thermometer} label="WARM лиды" value={stats?.warm ?? '—'} color="text-amber-400" />
        <StatCard icon={Snowflake} label="COLD лиды" value={stats?.cold ?? '—'} color="text-blue-300" />
        <StatCard icon={TrendingUp} label="Новых за неделю" value={stats?.new_week ?? '—'} color="text-purple-400" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Funnel by tier */}
        <div className="card">
          <h2 className="text-sm font-medium text-muted uppercase tracking-wide mb-4">Воронка по тирам</h2>
          {tierData.length > 0 ? (
            <div className="flex items-center gap-4">
              <ResponsiveContainer width={140} height={140}>
                <PieChart>
                  <Pie data={tierData} dataKey="cnt" nameKey="tier" cx="50%" cy="50%" outerRadius={60}>
                    {tierData.map((entry: { tier: string }, i: number) => (
                      <Cell key={i} fill={TIER_COLORS[entry.tier as keyof typeof TIER_COLORS] ?? '#4b5563'} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#1a1d27', border: '1px solid #2a2d3a', borderRadius: 8 }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2 flex-1">
                {tierData.map((t: { tier: string; cnt: number }) => (
                  <div key={t.tier} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full inline-block" style={{
                        background: TIER_COLORS[t.tier as keyof typeof TIER_COLORS] ?? '#4b5563'
                      }} />
                      <span className="text-muted">{t.tier}</span>
                    </div>
                    <span className="font-bold">{t.cnt}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted">Нет данных</p>
          )}
        </div>

        {/* Status pipeline */}
        <div className="card">
          <h2 className="text-sm font-medium text-muted uppercase tracking-wide mb-4">Статусы лидов</h2>
          <div className="space-y-2">
            {statusData.length > 0 ? statusData.map((s: { status: string; cnt: number }) => {
              const max = Math.max(...statusData.map((x: { cnt: number }) => x.cnt))
              const pct = Math.round(s.cnt / max * 100)
              const color = s.status === 'qualified' ? 'bg-green-500' : s.status === 'contacted' ? 'bg-blue-500' : s.status === 'lost' ? 'bg-red-500' : 'bg-indigo-500'
              return (
                <div key={s.status}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-muted capitalize">{s.status}</span>
                    <span className="font-medium">{s.cnt}</span>
                  </div>
                  <div className="h-1.5 bg-border rounded-full overflow-hidden">
                    <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )
            }) : <p className="text-sm text-muted">Нет данных</p>}
          </div>
          {funnel?.vacancies && (
            <div className="mt-4 pt-4 border-t border-border">
              <p className="text-xs text-muted mb-2">Вакансии (фильтр)</p>
              <div className="flex gap-4 text-xs">
                <span className="text-green-400">✓ Принято: {funnel.vacancies.accepted}</span>
                <span className="text-red-400">✗ Отклонено: {funnel.vacancies.rejected}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Recent leads */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-muted uppercase tracking-wide">Последние лиды</h2>
          <Link to="/leads" className="text-xs text-accent hover:underline">Все лиды →</Link>
        </div>
        {stats?.recent_leads?.length > 0 ? (
          <div className="space-y-2">
            {stats.recent_leads.map((lead: { id: number; full_name: string; username: string; tier: string; status: string; created_at: string }) => (
              <Link
                key={lead.id}
                to={`/leads/${lead.id}`}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{lead.full_name || `Lead #${lead.id}`}</p>
                  {lead.username && <p className="text-xs text-muted">@{lead.username}</p>}
                </div>
                <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                  lead.tier === 'HOT' ? 'bg-red-500/20 text-red-400' :
                  lead.tier === 'WARM' ? 'bg-amber-500/20 text-amber-400' :
                  'bg-blue-500/20 text-blue-400'
                }`}>{lead.tier}</span>
                <span className="text-xs text-muted flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {lead.created_at ? formatDistanceToNow(new Date(lead.created_at), { addSuffix: true, locale: ru }) : '—'}
                </span>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">Нет лидов</p>
        )}
      </div>
    </div>
  )
}
