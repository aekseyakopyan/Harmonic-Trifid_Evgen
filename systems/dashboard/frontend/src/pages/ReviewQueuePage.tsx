import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { CheckCircle, XCircle } from 'lucide-react'

interface PendingVacancy {
  id: number
  hash: string
  text: string
  direction: string
  source: string
  contact_link: string
  score: number | null
  draft_response: string
  last_seen: string
}

export default function ReviewQueuePage() {
  const [page, setPage] = useState(0)
  const limit = 20
  const qc = useQueryClient()

  const { data, isLoading } = useQuery<{ total: number; items: PendingVacancy[] }>({
    queryKey: ['pending-vacancies', page],
    queryFn: () =>
      axios.get('/api/vacancies/pending', { params: { skip: page * limit, limit } }).then(r => r.data),
    refetchInterval: 30000,
  })

  const approve = useMutation({
    mutationFn: (hash: string) => axios.post(`/api/vacancies/${hash}/approve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pending-vacancies'] }),
  })

  const skip = useMutation({
    mutationFn: (hash: string) => axios.post(`/api/vacancies/${hash}/skip_draft`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pending-vacancies'] }),
  })

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Лиды на подтверждение</h1>
        <span className="text-sm text-muted">Ожидают: {data?.total ?? '...'}</span>
      </div>

      {isLoading ? (
        <div className="text-muted text-sm">Загрузка...</div>
      ) : (
        <div className="space-y-4">
          {data?.items?.map(v => (
            <div key={v.hash} className="bg-card border border-border rounded-lg p-4 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex flex-wrap gap-2 items-center">
                  {v.direction && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400">{v.direction}</span>
                  )}
                  {v.score != null && (
                    <span className="text-xs text-muted">score: {v.score}</span>
                  )}
                  {v.contact_link && (
                    <span className="text-xs text-accent truncate max-w-[220px]">{v.contact_link}</span>
                  )}
                  {v.source && (
                    <span className="text-xs text-muted truncate max-w-[160px]">{v.source}</span>
                  )}
                </div>
                <span className="text-xs text-muted shrink-0">{v.last_seen?.slice(0, 16)}</span>
              </div>

              {/* Original vacancy */}
              <div className="text-xs text-white/60 bg-surface rounded p-2.5 leading-relaxed border border-border/40 whitespace-pre-wrap">
                {v.text}
              </div>

              {/* Draft response */}
              <div className="text-sm text-green-300/90 bg-green-950/20 border border-green-500/20 rounded-lg p-3 leading-relaxed whitespace-pre-wrap">
                {v.draft_response}
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => approve.mutate(v.hash)}
                  disabled={approve.isPending}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-green-600/20 hover:bg-green-600/30 text-green-400 text-sm border border-green-600/30 transition-colors disabled:opacity-50"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  Отправить
                </button>
                <button
                  onClick={() => skip.mutate(v.hash)}
                  disabled={skip.isPending}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-red-600/10 hover:bg-red-600/20 text-red-400 text-sm border border-red-600/30 transition-colors disabled:opacity-50"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  Пропустить
                </button>
              </div>
            </div>
          ))}

          {data?.items?.length === 0 && (
            <div className="text-center text-muted text-sm py-16">Нет лидов на подтверждение</div>
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
