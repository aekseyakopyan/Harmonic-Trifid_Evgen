import { useState, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { leadsApi } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'
import { Lead } from '../types'
import { Search, Download, Archive, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'
import clsx from 'clsx'
import { formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'

const TIER_OPTIONS = ['', 'HOT', 'WARM', 'COLD']
const STATUS_OPTIONS = ['', 'new', 'contacted', 'qualified', 'lost']
const PAGE_SIZE = 50

function TierBadge({ tier }: { tier: string | null }) {
  if (!tier || tier === 'COLD') return <span className="badge-cold">COLD</span>
  if (tier === 'HOT') return <span className="badge-hot">HOT</span>
  if (tier === 'WARM') return <span className="badge-warm">WARM</span>
  return <span className="badge-cold">{tier}</span>
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score))
  const color = pct >= 70 ? 'bg-red-500' : pct >= 40 ? 'bg-amber-500' : 'bg-blue-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-border rounded-full overflow-hidden">
        <div className={clsx('h-full rounded-full', color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted">{score.toFixed(0)}</span>
    </div>
  )
}

export default function LeadsFeedPage() {
  const [search, setSearch] = useState('')
  const [tier, setTier] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(0)
  const [archived, setArchived] = useState(false)
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['leads', search, tier, status, archived, page],
    queryFn: () =>
      leadsApi.list({
        search: search || undefined,
        tier: tier || undefined,
        status: status || undefined,
        is_archived: archived ? 1 : 0,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }).then(r => r.data),
  })

  useWebSocket('leads', useCallback(() => {
    qc.invalidateQueries({ queryKey: ['leads'] })
  }, [qc]))

  const handleExport = async () => {
    const res = await leadsApi.export({ tier: tier || undefined, status: status || undefined })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'leads.csv'
    a.click()
  }

  const leads: Lead[] = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold">Лиды</h1>
          <p className="text-sm text-muted mt-0.5">Всего: {total}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleExport} className="btn-ghost flex items-center gap-1.5">
            <Download className="w-4 h-4" /> CSV
          </button>
          <button
            onClick={() => setArchived(!archived)}
            className={clsx('btn-ghost flex items-center gap-1.5', archived && 'text-white')}
          >
            <Archive className="w-4 h-4" />
            {archived ? 'Архив' : 'Активные'}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
          <input
            className="input w-full pl-9"
            placeholder="Поиск по имени / username"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(0) }}
          />
        </div>
        <select
          className="input"
          value={tier}
          onChange={e => { setTier(e.target.value); setPage(0) }}
        >
          {TIER_OPTIONS.map(t => (
            <option key={t} value={t}>{t || 'Все тиры'}</option>
          ))}
        </select>
        <select
          className="input"
          value={status}
          onChange={e => { setStatus(e.target.value); setPage(0) }}
        >
          {STATUS_OPTIONS.map(s => (
            <option key={s} value={s}>{s || 'Все статусы'}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-muted text-left">
              <th className="px-4 py-3 font-medium">Лид</th>
              <th className="px-4 py-3 font-medium">Тир</th>
              <th className="px-4 py-3 font-medium">Скор</th>
              <th className="px-4 py-3 font-medium">Ниша</th>
              <th className="px-4 py-3 font-medium">Статус</th>
              <th className="px-4 py-3 font-medium">Последнее взаимодействие</th>
              <th className="px-4 py-3 font-medium w-20"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-muted">
                  <RefreshCw className="w-5 h-5 animate-spin mx-auto" />
                </td>
              </tr>
            )}
            {!isLoading && leads.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-muted">Лиды не найдены</td>
              </tr>
            )}
            {leads.map(lead => (
              <tr key={lead.id} className="border-b border-border/50 hover:bg-white/3 transition-colors">
                <td className="px-4 py-3">
                  <Link to={`/leads/${lead.id}`} className="hover:text-accent transition-colors">
                    <div className="font-medium">{lead.full_name || '—'}</div>
                    {lead.username && (
                      <div className="text-xs text-muted">@{lead.username}</div>
                    )}
                  </Link>
                </td>
                <td className="px-4 py-3"><TierBadge tier={lead.tier} /></td>
                <td className="px-4 py-3"><ScoreBar score={lead.lead_score} /></td>
                <td className="px-4 py-3 text-muted text-xs">{lead.niche || '—'}</td>
                <td className="px-4 py-3">
                  <span className="text-xs text-muted">{lead.status}</span>
                </td>
                <td className="px-4 py-3 text-xs text-muted">
                  {lead.last_interaction
                    ? formatDistanceToNow(new Date(lead.last_interaction), { addSuffix: true, locale: ru })
                    : '—'}
                </td>
                <td className="px-4 py-3">
                  <Link to={`/leads/${lead.id}`} className="btn-ghost py-1 px-2 text-xs">
                    →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-sm text-muted">
            {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} из {total}
          </span>
          <div className="flex gap-2">
            <button
              className="btn-ghost"
              disabled={page === 0}
              onClick={() => setPage(p => p - 1)}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              className="btn-ghost"
              disabled={page >= totalPages - 1}
              onClick={() => setPage(p => p + 1)}
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
