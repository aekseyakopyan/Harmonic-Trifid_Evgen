import { useQuery } from '@tanstack/react-query'
import { analyticsApi } from '../api/client'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { RefreshCw, Filter, CheckCircle, XCircle } from 'lucide-react'

const LEVEL_COLORS: Record<string, string> = {
  L1: '#ef4444',
  L2: '#f59e0b',
  ML: '#6366f1',
  LLM: '#8b5cf6',
  Other: '#6b7280',
}

export default function FilterStatsPage() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['filter-stats'],
    queryFn: () => analyticsApi.filterStats().then(r => r.data),
  })

  const total = (data?.total_accepted ?? 0) + (data?.total_rejected ?? 0)
  const acceptRate = total > 0 ? ((data?.total_accepted ?? 0) / total * 100).toFixed(1) : '0'
  const rejectRate = total > 0 ? ((data?.total_rejected ?? 0) / total * 100).toFixed(1) : '0'

  const byLevelData = Object.entries(data?.by_level ?? {}).map(([level, cnt]) => ({ level, cnt: cnt as number }))
  const topReasons = (data?.top_reasons ?? []).slice(0, 20)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2">
            <Filter className="w-5 h-5 text-accent" /> Статистика фильтрации
          </h1>
          <p className="text-sm text-muted mt-0.5">Анализ причин отклонения вакансий по уровням</p>
        </div>
        <button onClick={() => refetch()} className="btn-ghost flex items-center gap-1.5 text-sm">
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} /> Обновить
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card text-center">
          <p className="text-xs text-muted mb-1">Всего обработано</p>
          <p className="text-2xl font-bold">{total.toLocaleString()}</p>
        </div>
        <div className="card text-center">
          <p className="text-xs text-muted mb-1 flex items-center justify-center gap-1">
            <CheckCircle className="w-3 h-3 text-green-400" /> Принято
          </p>
          <p className="text-2xl font-bold text-green-400">{(data?.total_accepted ?? 0).toLocaleString()}</p>
          <p className="text-xs text-muted">{acceptRate}%</p>
        </div>
        <div className="card text-center">
          <p className="text-xs text-muted mb-1 flex items-center justify-center gap-1">
            <XCircle className="w-3 h-3 text-red-400" /> Отклонено
          </p>
          <p className="text-2xl font-bold text-red-400">{(data?.total_rejected ?? 0).toLocaleString()}</p>
          <p className="text-xs text-muted">{rejectRate}%</p>
        </div>
        <div className="card text-center">
          <p className="text-xs text-muted mb-1">Уровней фильтрации</p>
          <p className="text-2xl font-bold">{byLevelData.length}</p>
        </div>
      </div>

      {/* By filter level */}
      {byLevelData.length > 0 && (
        <div className="card">
          <h2 className="text-sm font-medium text-muted uppercase tracking-wide mb-4">По уровням фильтрации</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {byLevelData.map(({ level, cnt }) => (
              <div key={level} className="bg-surface rounded-lg p-3 text-center border border-border">
                <div className="text-xs font-bold mb-1" style={{ color: LEVEL_COLORS[level] ?? '#6b7280' }}>{level}</div>
                <div className="text-xl font-bold">{cnt.toLocaleString()}</div>
                <div className="mt-1.5 h-1 bg-border rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${data?.total_rejected ? Math.round(cnt / (data.total_rejected as number) * 100) : 0}%`,
                      backgroundColor: LEVEL_COLORS[level] ?? '#6b7280'
                    }}
                  />
                </div>
                <div className="text-xs text-muted mt-1">
                  {data?.total_rejected ? Math.round(cnt / (data.total_rejected as number) * 100) : 0}% отклонённых
                </div>
              </div>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={byLevelData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" />
              <XAxis dataKey="level" tick={{ fontSize: 12, fill: '#6b7280' }} />
              <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
              <Tooltip contentStyle={{ background: '#1a1d27', border: '1px solid #2a2d3a', borderRadius: 8 }} />
              <Bar dataKey="cnt" radius={[4, 4, 0, 0]}>
                {byLevelData.map(({ level }, i) => (
                  <Cell key={i} fill={LEVEL_COLORS[level] ?? '#6b7280'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Top rejection reasons */}
      {topReasons.length > 0 ? (
        <div className="card">
          <h2 className="text-sm font-medium text-muted uppercase tracking-wide mb-4">
            Топ причин отклонения
          </h2>
          <div className="space-y-2 max-h-[400px] overflow-auto">
            {topReasons.map((r: { rejection_reason: string; cnt: number }, i: number) => {
              const maxCnt = topReasons[0]?.cnt ?? 1
              const pct = Math.round(r.cnt / maxCnt * 100)
              const level = r.rejection_reason?.split(':')[0]?.split('_')[0] ?? 'Other'
              return (
                <div key={i} className="flex items-center gap-3">
                  <div className="w-5 text-xs text-muted text-right shrink-0">{i + 1}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-xs font-mono truncate max-w-[280px]" title={r.rejection_reason}>
                        <span className="mr-1.5 text-[10px] px-1 rounded" style={{ backgroundColor: (LEVEL_COLORS[level] ?? '#6b7280') + '30', color: LEVEL_COLORS[level] ?? '#6b7280' }}>
                          {level}
                        </span>
                        {r.rejection_reason}
                      </span>
                      <span className="text-xs text-muted shrink-0 ml-2">{r.cnt.toLocaleString()}</span>
                    </div>
                    <div className="h-1 bg-border rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${pct}%`, backgroundColor: LEVEL_COLORS[level] ?? '#6b7280' }}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ) : !isLoading && (
        <div className="card text-center py-10">
          <Filter className="w-8 h-8 text-muted mx-auto mb-3" />
          <p className="text-muted text-sm">Нет данных о причинах отклонения</p>
          <p className="text-xs text-muted mt-1">Убедитесь, что поле rejection_reason сохраняется в vacancies.db</p>
        </div>
      )}
    </div>
  )
}
