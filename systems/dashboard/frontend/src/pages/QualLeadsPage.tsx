import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { Link } from 'react-router-dom'

const TIER_COLORS: Record<string, string> = {
  HOT: 'bg-red-500/20 text-red-400',
  WARM: 'bg-orange-500/20 text-orange-400',
  COLD: 'bg-blue-500/20 text-blue-400',
}

const STATUS_LABELS: Record<string, string> = {
  new: 'Новый',
  contacted: 'Написали',
  qualified: 'Квал',
  lost: 'Потерян',
}

export default function QualLeadsPage() {
  const [tier, setTier] = useState<string>('')
  const [page, setPage] = useState(0)
  const limit = 50

  const { data, isLoading } = useQuery<{ total: number; items: Record<string, string | number | null>[] }>({
    queryKey: ['qual-leads', tier, page],
    queryFn: () =>
      axios
        .get('/api/leads/', {
          params: {
            tier: tier || undefined,
            is_archived: 0,
            skip: page * limit,
            limit,
            sort: 'last_interaction',
            order: 'desc',
          },
        })
        .then(r => r.data),
    refetchInterval: 30000,
    placeholderData: prev => prev,
  })

  const tiers = [
    { value: '', label: 'Все' },
    { value: 'HOT', label: '🔥 HOT' },
    { value: 'WARM', label: '🟡 WARM' },
    { value: 'COLD', label: '❄️ COLD' },
  ]

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Квал лиды</h1>
        <span className="text-sm text-muted">Всего: {data?.total ?? '...'}</span>
      </div>

      {/* Tier filter */}
      <div className="flex gap-2 flex-wrap">
        {tiers.map(t => (
          <button
            key={t.value}
            onClick={() => { setTier(t.value); setPage(0) }}
            className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
              tier === t.value
                ? 'border-accent bg-accent/10 text-accent'
                : 'border-border text-muted hover:text-white hover:border-white/20'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-muted text-sm">Загрузка...</div>
      ) : (
        <div className="space-y-2">
          {data?.items?.map(lead => (
            <Link
              key={lead.id}
              to={`/leads/${lead.id}`}
              className="flex items-center justify-between gap-3 bg-card border border-border rounded-lg px-4 py-3 hover:border-accent/30 transition-colors"
            >
              <div className="flex items-center gap-2 flex-wrap min-w-0">
                {lead.tier && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${TIER_COLORS[lead.tier as string] ?? 'bg-gray-500/20 text-gray-400'}`}>
                    {lead.tier as string}
                  </span>
                )}
                {lead.status && STATUS_LABELS[lead.status as string] && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 text-muted shrink-0">
                    {STATUS_LABELS[lead.status as string]}
                  </span>
                )}
                <span className="text-sm font-medium truncate">
                  {(lead.full_name as string) || (lead.username ? `@${lead.username}` : `Lead #${lead.id}`)}
                </span>
                {lead.username && lead.full_name && (
                  <span className="text-xs text-muted shrink-0">@{lead.username as string}</span>
                )}
                {lead.niche && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 shrink-0">{lead.niche as string}</span>
                )}
              </div>
              <div className="flex items-center gap-3 shrink-0">
                {lead.lead_score != null && (
                  <span className="text-xs text-muted">score: {lead.lead_score}</span>
                )}
                <span className="text-xs text-muted">{(lead.last_interaction as string)?.slice(0, 16)}</span>
              </div>
            </Link>
          ))}

          {data?.items?.length === 0 && (
            <div className="text-center text-muted text-sm py-16">Нет лидов</div>
          )}
        </div>
      )}

      {(data?.total ?? 0) > limit && (
        <div className="flex gap-2 items-center justify-center pt-2">
          <button
            disabled={page === 0}
            onClick={() => setPage(p => p - 1)}
            className="px-3 py-1.5 rounded-lg border border-border text-sm text-muted hover:text-white disabled:opacity-40"
          >
            ← Назад
          </button>
          <span className="text-sm text-muted">{page + 1} / {Math.ceil((data?.total ?? 0) / limit)}</span>
          <button
            disabled={(page + 1) * limit >= (data?.total ?? 0)}
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
