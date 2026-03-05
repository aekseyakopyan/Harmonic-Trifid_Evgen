import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { analyticsApi } from '../api/client'
import { AnalyticsOverview } from '../types'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'

const PERIOD_OPTIONS = [
  { value: 'day', label: 'День' },
  { value: 'week', label: 'Неделя' },
  { value: 'month', label: 'Месяц' },
]

const COLORS = ['#6366f1', '#f59e0b', '#ef4444', '#10b981', '#3b82f6', '#8b5cf6']

function KpiCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="card">
      <p className="text-xs text-muted mb-1">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
      {sub && <p className="text-xs text-muted mt-0.5">{sub}</p>}
    </div>
  )
}

export default function AnalyticsPage() {
  const [period, setPeriod] = useState<'day' | 'week' | 'month'>('week')

  const { data: overview } = useQuery({
    queryKey: ['analytics-overview', period],
    queryFn: () => analyticsApi.overview(period).then(r => r.data as AnalyticsOverview),
  })

  const { data: timeline } = useQuery({
    queryKey: ['analytics-timeline', period],
    queryFn: () => analyticsApi.timeline(period).then(r => r.data as { date: string; count: number }[]),
  })

  const { data: byNiche } = useQuery({
    queryKey: ['analytics-niche'],
    queryFn: () => analyticsApi.byNiche().then(r => r.data as { niche: string; cnt: number }[]),
  })

  const { data: bySource } = useQuery({
    queryKey: ['analytics-source'],
    queryFn: () => analyticsApi.bySource().then(r => r.data as { source_channel: string; cnt: number }[]),
  })

  const { data: alexeyLoad } = useQuery({
    queryKey: ['analytics-alexey'],
    queryFn: () => analyticsApi.alexeyLoad().then(r => r.data),
  })

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Аналитика</h1>
        <div className="flex gap-1">
          {PERIOD_OPTIONS.map(p => (
            <button
              key={p.value}
              className={`px-3 py-1.5 rounded text-sm transition-colors ${
                period === p.value ? 'bg-accent text-white' : 'btn-ghost'
              }`}
              onClick={() => setPeriod(p.value as 'day' | 'week' | 'month')}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI row */}
      {overview && (
        <div className="grid grid-cols-4 gap-4">
          <KpiCard label="Всего лидов" value={overview.total_leads} />
          <KpiCard label="Новых за период" value={overview.new_leads} />
          <KpiCard
            label="HOT / WARM"
            value={`${overview.hot_leads} / ${overview.warm_leads}`}
            sub={`Конверсия ${overview.conversion_rate}%`}
          />
          <KpiCard
            label="Диалоги"
            value={overview.dialogs_active}
            sub={`${overview.dialogs_in_period} за период`}
          />
        </div>
      )}

      {/* Timeline */}
      <div className="card">
        <h2 className="text-sm font-medium text-muted uppercase tracking-wide mb-4">
          Поток лидов
        </h2>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={timeline ?? []}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6b7280' }} />
            <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
            <Tooltip
              contentStyle={{ background: '#1a1d27', border: '1px solid #2a2d3a', borderRadius: 8 }}
              labelStyle={{ color: '#fff' }}
            />
            <Line type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* By niche */}
        <div className="card">
          <h2 className="text-sm font-medium text-muted uppercase tracking-wide mb-4">По нишам</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={(byNiche ?? []).slice(0, 10)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" />
              <XAxis type="number" tick={{ fontSize: 10, fill: '#6b7280' }} />
              <YAxis dataKey="niche" type="category" tick={{ fontSize: 10, fill: '#6b7280' }} width={80} />
              <Tooltip
                contentStyle={{ background: '#1a1d27', border: '1px solid #2a2d3a', borderRadius: 8 }}
              />
              <Bar dataKey="cnt" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* By source */}
        <div className="card">
          <h2 className="text-sm font-medium text-muted uppercase tracking-wide mb-4">По источникам</h2>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={(bySource ?? []).slice(0, 8)}
                dataKey="cnt"
                nameKey="source_channel"
                cx="50%"
                cy="50%"
                outerRadius={70}
                label={({ source_channel, percent }) =>
                  `${String(source_channel).slice(0, 12)} ${(percent * 100).toFixed(0)}%`
                }
                labelLine={false}
              >
                {(bySource ?? []).slice(0, 8).map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#1a1d27', border: '1px solid #2a2d3a', borderRadius: 8 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Alexey load */}
      {alexeyLoad && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-muted uppercase tracking-wide">Нагрузка Алексея (7д)</h2>
            <div className="flex gap-4 text-sm">
              <span className="text-muted">Авто: <span className="text-white">{alexeyLoad.auto_sent_7d}</span></span>
              <span className="text-muted">Ручных: <span className="text-amber-400">{alexeyLoad.manual_sent_7d}</span></span>
              <span className="text-muted">Всего: <span className="text-white">{alexeyLoad.total_sent_7d}</span></span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={150}>
            <BarChart data={alexeyLoad.by_hour ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#6b7280' }} />
              <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} />
              <Tooltip
                contentStyle={{ background: '#1a1d27', border: '1px solid #2a2d3a', borderRadius: 8 }}
              />
              <Bar dataKey="cnt" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
