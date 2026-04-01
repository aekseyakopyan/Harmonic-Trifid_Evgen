import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

const STATUS_LABELS: Record<string, string> = {
  accepted: 'Принят',
  rejected: 'Отклонён',
  no_draft_skip: 'Пропущен',
  blacklist_skip: 'Блок-лист',
  sent: 'Отправлен',
  active_dialogue_skip: 'Диалог',
}

const STATUS_COLORS: Record<string, string> = {
  accepted: 'bg-green-500/20 text-green-400',
  rejected: 'bg-red-500/20 text-red-400',
  no_draft_skip: 'bg-yellow-500/20 text-yellow-400',
  blacklist_skip: 'bg-gray-500/20 text-gray-400',
  sent: 'bg-blue-500/20 text-blue-400',
  active_dialogue_skip: 'bg-purple-500/20 text-purple-400',
}

export default function VacanciesPage() {
  const [status, setStatus] = useState('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const limit = 100

  const { data, isLoading } = useQuery<{ total: number; items: Record<string, string>[] }>({
    queryKey: ['vacancies', status, search, page],
    queryFn: () =>
      axios
        .get('/api/vacancies/', {
          params: { status: status === 'all' ? undefined : status, search: search || undefined, skip: page * limit, limit },
        })
        .then(r => r.data),
    placeholderData: (prev) => prev,
  })

  const { data: stats } = useQuery({
    queryKey: ['vacancies-stats'],
    queryFn: () => axios.get('/api/vacancies/stats').then(r => r.data),
    refetchInterval: 30000,
  })

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Вакансии</h1>
        <span className="text-sm text-muted">Всего: {data?.total ?? '...'}</span>
      </div>

      {/* Stats */}
      {stats && (
        <div className="flex gap-3 flex-wrap">
          {stats.by_status.map((s: { status: string; cnt: number }) => (
            <button
              key={s.status}
              onClick={() => { setStatus(s.status === status ? 'all' : s.status); setPage(0) }}
              className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                status === s.status
                  ? 'border-accent bg-accent/10 text-accent'
                  : 'border-border text-muted hover:text-white hover:border-white/20'
              }`}
            >
              {STATUS_LABELS[s.status] ?? s.status}: {s.cnt}
            </button>
          ))}
          {stats.today > 0 && (
            <span className="px-3 py-1.5 rounded-lg text-sm border border-border text-muted">
              Сегодня: {stats.today}
            </span>
          )}
        </div>
      )}

      {/* Search */}
      <input
        className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
        placeholder="Поиск по тексту, источнику, контакту..."
        value={search}
        onChange={e => { setSearch(e.target.value); setPage(0) }}
      />

      {/* Table */}
      {isLoading ? (
        <div className="text-muted text-sm">Загрузка...</div>
      ) : (
        <div className="space-y-2">
          {data?.items?.map((v: Record<string, string>) => (
            <div key={v.id} className="bg-card border border-border rounded-lg p-3 space-y-1.5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[v.status] ?? 'bg-gray-500/20 text-gray-400'}`}>
                    {STATUS_LABELS[v.status] ?? v.status}
                  </span>
                  {v.direction && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400">{v.direction}</span>
                  )}
                  {v.source && (
                    <span className="text-xs text-muted truncate max-w-[200px]">{v.source}</span>
                  )}
                </div>
                <span className="text-xs text-muted shrink-0">{v.last_seen?.slice(0, 16) ?? v.created_at?.slice(0, 16)}</span>
              </div>

              <p className="text-sm text-white/80 leading-relaxed">{v.text}</p>

              {v.contact_link && (
                <div className="text-xs text-accent truncate">→ {v.contact_link}</div>
              )}
              {v.rejection_reason && (
                <div className="text-xs text-red-400/70">Причина: {v.rejection_reason}</div>
              )}
              {v.draft_response && (
                <div className="text-xs text-green-400/70 border-t border-border/50 pt-1.5 mt-1.5">
                  Черновик: {v.draft_response}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {data?.total > limit && (
        <div className="flex gap-2 items-center justify-center pt-2">
          <button
            disabled={page === 0}
            onClick={() => setPage(p => p - 1)}
            className="px-3 py-1.5 rounded-lg border border-border text-sm text-muted hover:text-white disabled:opacity-40"
          >
            ← Назад
          </button>
          <span className="text-sm text-muted">{page + 1} / {Math.ceil(data.total / limit)}</span>
          <button
            disabled={(page + 1) * limit >= data.total}
            onClick={() => setPage(p => p + 1)}
            className="px-3 py-1.5 rounded-lg border border-border text-sm text-muted hover:text-white disabled:opacity-40"
          >
            Вперёд →
          </button>
        </div>
      )}
    </div>
  )
}
