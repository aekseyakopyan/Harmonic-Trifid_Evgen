import { useState, useCallback } from 'react'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { leadsApi } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'
import { Lead } from '../types'
import { Search, Download, Archive, RefreshCw, ChevronLeft, ChevronRight, Star, CheckSquare, Square, Flame, Thermometer, Snowflake, X, MessageSquare, Ban, Copy, Check, Send } from 'lucide-react'
import clsx from 'clsx'
import { formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'

const TIER_OPTIONS = ['', 'HOT', 'WARM', 'COLD']
const STATUS_OPTIONS = ['', 'new', 'contacted', 'qualified', 'lost']
const QUAL_OPTIONS = [
  { value: '', label: 'Любая оценка' },
  { value: '5', label: '★★★★★  5' },
  { value: '4', label: '★★★★☆  4' },
  { value: '3', label: '★★★☆☆  3' },
  { value: '1', label: '★☆☆☆☆  ≤2' },
]
const PAGE_SIZE = 50

function TierBadge({ tier }: { tier: string | null }) {
  if (tier === 'HOT') return <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-500/20 text-red-400">HOT</span>
  if (tier === 'WARM') return <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-500/20 text-amber-400">WARM</span>
  return <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-500/20 text-blue-400">COLD</span>
}

function ScoreBar({ score }: { score: number | null }) {
  const s = score ?? 0
  const pct = Math.min(100, Math.max(0, s))
  const color = pct >= 70 ? 'bg-red-500' : pct >= 40 ? 'bg-amber-500' : 'bg-blue-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-border rounded-full overflow-hidden">
        <div className={clsx('h-full rounded-full', color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted">{s.toFixed(0)}</span>
    </div>
  )
}

function StarRating({ value }: { value: number | null }) {
  if (value == null) return <span className="text-muted text-xs">—</span>
  return (
    <span className={`text-xs font-bold ${value >= 4 ? 'text-green-400' : value === 3 ? 'text-amber-400' : 'text-red-400'}`}>
      {'★'.repeat(value)}{'☆'.repeat(5 - value)}
    </span>
  )
}

function QuickTierButtons({ leadId, currentTier, onDone }: { leadId: number; currentTier: string | null; onDone: () => void }) {
  const qc = useQueryClient()
  const patch = useMutation({
    mutationFn: (tier: string) => leadsApi.patch(leadId, { tier }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['leads'] }); onDone() },
  })
  return (
    <div className="flex gap-1">
      {[
        { t: 'HOT', icon: <Flame className="w-3 h-3" />, cls: 'text-red-400 hover:bg-red-500/20' },
        { t: 'WARM', icon: <Thermometer className="w-3 h-3" />, cls: 'text-amber-400 hover:bg-amber-500/20' },
        { t: 'COLD', icon: <Snowflake className="w-3 h-3" />, cls: 'text-blue-400 hover:bg-blue-500/20' },
      ].map(({ t, icon, cls }) => (
        <button
          key={t}
          title={t}
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); patch.mutate(t) }}
          className={clsx('p-1 rounded transition-colors', cls, currentTier === t ? 'opacity-50 cursor-default' : '')}
          disabled={currentTier === t || patch.isPending}
        >
          {icon}
        </button>
      ))}
    </div>
  )
}

function DraftModal({ lead, draft, onClose }: { lead: Lead; draft: string; onClose: () => void }) {
  const [copied, setCopied] = useState(false)
  const [sent, setSent] = useState(false)
  const [sending, setSending] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(draft)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  const sendViaKsenia = async () => {
    setSending(true)
    try {
      await leadsApi.sendOutreach(lead.id)
      setSent(true)
      setTimeout(onClose, 1500)
    } catch {
      alert('Не удалось поставить в очередь — нет вакансии в очереди или ошибка сервера')
    } finally {
      setSending(false)
    }
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-card border border-border rounded-xl p-5 max-w-lg w-full mx-4 space-y-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold">Написать {lead.full_name || `@${lead.username}`}</h3>
            {lead.niche && <p className="text-xs text-muted mt-0.5">{lead.niche} · {lead.source_channel}</p>}
          </div>
          <button onClick={onClose} className="text-muted hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="bg-surface rounded-lg p-3 text-sm text-white/80 whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto border border-border/50">
          {draft}
        </div>
        <div className="flex gap-2">
          <button
            onClick={copy}
            className={clsx('flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-sm border transition-colors',
              copied ? 'border-green-500/40 text-green-400 bg-green-500/10' : 'border-border text-muted hover:text-white hover:border-white/20'
            )}
          >
            {copied ? <><Check className="w-3.5 h-3.5" /> Скопировано</> : <><Copy className="w-3.5 h-3.5" /> Копировать</>}
          </button>
          <button
            onClick={sendViaKsenia}
            disabled={sending || sent}
            className={clsx('flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-sm border transition-colors font-medium',
              sent ? 'border-green-500/40 text-green-400 bg-green-500/10' :
              'border-accent/60 text-accent bg-accent/10 hover:bg-accent/20'
            )}
          >
            {sent ? <><Check className="w-3.5 h-3.5" /> Отправлено в очередь</> :
             sending ? <><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Отправляю…</> :
             <><Send className="w-3.5 h-3.5" /> Отправить через Ксению</>}
          </button>
        </div>
        {lead.username && (
          <a
            href={`https://t.me/${lead.username}`}
            target="_blank"
            rel="noreferrer"
            className="block text-center text-xs text-muted hover:text-white transition-colors"
          >
            Открыть @{lead.username} в Telegram →
          </a>
        )}
      </div>
    </div>
  )
}

export default function LeadsFeedPage() {
  const [search, setSearch] = useState('')
  const [tier, setTier] = useState('')
  const [status, setStatus] = useState('')
  const [qualFilter, setQualFilter] = useState('')
  const [page, setPage] = useState(0)
  const [archived, setArchived] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [hoverRow, setHoverRow] = useState<number | null>(null)
  const [draftModal, setDraftModal] = useState<{ lead: Lead; draft: string } | null>(null)
  const [spamToast, setSpamToast] = useState<string | null>(null)
  const qc = useQueryClient()

  const spamMutation = useMutation({
    mutationFn: (lead: Lead) => leadsApi.markSpam(lead.id),
    onSuccess: (res) => {
      const { reason, username } = res.data
      setSpamToast(`@${username} → ${reason}`)
      setTimeout(() => setSpamToast(null), 5000)
      qc.invalidateQueries({ queryKey: ['leads'] })
    },
  })

  const writeMutation = useMutation({
    mutationFn: async (lead: Lead) => {
      const [draftRes] = await Promise.all([
        leadsApi.draft(lead.id),
        leadsApi.queueOutreach(lead.id),
      ])
      return { lead, draft: draftRes.data.draft || 'Черновик не найден — напиши вручную' }
    },
    onSuccess: ({ lead, draft }) => {
      setDraftModal({ lead, draft })
      qc.invalidateQueries({ queryKey: ['leads'] })
    },
  })

  const { data, isLoading } = useQuery({
    queryKey: ['leads', search, tier, status, archived, page, qualFilter],
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

  const bulkMutation = useMutation({
    mutationFn: ({ action, value }: { action: string; value?: string }) =>
      leadsApi.bulk(Array.from(selectedIds), action, value),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['leads'] })
      setSelectedIds(new Set())
    },
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
    setTimeout(() => URL.revokeObjectURL(url), 100)
  }

  // Client-side qual filter (backend doesn't support it yet)
  let leads: Lead[] = data?.items ?? []
  if (qualFilter === '5') leads = leads.filter(l => l.qual_score === 5)
  else if (qualFilter === '4') leads = leads.filter(l => l.qual_score === 4)
  else if (qualFilter === '3') leads = leads.filter(l => l.qual_score === 3)
  else if (qualFilter === '1') leads = leads.filter(l => l.qual_score != null && l.qual_score <= 2)

  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)

  const allSelected = leads.length > 0 && leads.every(l => selectedIds.has(l.id))
  const toggleAll = () => {
    if (allSelected) {
      setSelectedIds(prev => { const s = new Set(prev); leads.forEach(l => s.delete(l.id)); return s })
    } else {
      setSelectedIds(prev => { const s = new Set(prev); leads.forEach(l => s.add(l.id)); return s })
    }
  }
  const toggleOne = (id: number) => {
    setSelectedIds(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s })
  }

  const selCount = selectedIds.size

  return (
    <div className="p-4 md:p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold">Лиды</h1>
          <p className="text-sm text-muted mt-0.5">Всего: {total}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleExport} className="btn-ghost flex items-center gap-1.5 text-sm">
            <Download className="w-4 h-4" /> CSV
          </button>
          <button
            onClick={() => setArchived(!archived)}
            className={clsx('btn-ghost flex items-center gap-1.5 text-sm', archived && 'text-white')}
          >
            <Archive className="w-4 h-4" />
            {archived ? 'Архив' : 'Активные'}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-4">
        <div className="relative flex-1 min-w-[180px] max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
          <input
            className="input w-full pl-9"
            placeholder="Имя / username"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(0) }}
          />
        </div>
        <select className="input" value={tier} onChange={e => { setTier(e.target.value); setPage(0) }}>
          {TIER_OPTIONS.map(t => <option key={t} value={t}>{t || 'Все тиры'}</option>)}
        </select>
        <select className="input" value={status} onChange={e => { setStatus(e.target.value); setPage(0) }}>
          {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s || 'Все статусы'}</option>)}
        </select>
        <select className="input" value={qualFilter} onChange={e => setQualFilter(e.target.value)}>
          {QUAL_OPTIONS.map(q => <option key={q.value} value={q.value}>{q.label}</option>)}
        </select>
        {(tier || status || qualFilter || search) && (
          <button
            className="btn-ghost text-xs text-muted hover:text-white"
            onClick={() => { setTier(''); setStatus(''); setQualFilter(''); setSearch(''); setPage(0) }}
          >
            ✕ Сбросить
          </button>
        )}
      </div>

      {/* Bulk action bar */}
      {selCount > 0 && (
        <div className="flex items-center gap-3 mb-3 px-4 py-2.5 bg-accent/10 border border-accent/30 rounded-lg">
          <span className="text-sm font-medium text-accent">Выбрано: {selCount}</span>
          <div className="flex gap-2 ml-2">
            <button
              className="px-3 py-1 rounded text-xs bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
              onClick={() => bulkMutation.mutate({ action: 'set_tier', value: 'HOT' })}
              disabled={bulkMutation.isPending}
            >
              🔥 HOT
            </button>
            <button
              className="px-3 py-1 rounded text-xs bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 transition-colors"
              onClick={() => bulkMutation.mutate({ action: 'set_tier', value: 'WARM' })}
              disabled={bulkMutation.isPending}
            >
              🌡 WARM
            </button>
            <button
              className="px-3 py-1 rounded text-xs bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors"
              onClick={() => bulkMutation.mutate({ action: 'set_status', value: 'qualified' })}
              disabled={bulkMutation.isPending}
            >
              ✓ Квал
            </button>
            <button
              className="px-3 py-1 rounded text-xs bg-border text-muted hover:text-white transition-colors"
              onClick={() => { if (confirm(`Архивировать ${selCount} лидов?`)) bulkMutation.mutate({ action: 'archive' }) }}
              disabled={bulkMutation.isPending}
            >
              <Archive className="w-3 h-3 inline mr-1" />Архив
            </button>
          </div>
          <button
            className="ml-auto text-muted hover:text-white"
            onClick={() => setSelectedIds(new Set())}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Table with horizontal scroll */}
      <div className="card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[900px]">
            <thead>
              <tr className="border-b border-border text-muted text-left bg-card">
                <th className="px-3 py-3 w-8">
                  <button onClick={toggleAll} className="text-muted hover:text-white transition-colors">
                    {allSelected ? <CheckSquare className="w-4 h-4 text-accent" /> : <Square className="w-4 h-4" />}
                  </button>
                </th>
                <th className="px-4 py-3 font-medium whitespace-nowrap">Лид</th>
                <th className="px-4 py-3 font-medium whitespace-nowrap">Тир</th>
                <th className="px-4 py-3 font-medium whitespace-nowrap">Скор</th>
                <th className="px-4 py-3 font-medium whitespace-nowrap">
                  <span className="flex items-center gap-1"><Star className="w-3 h-3" />Целевой</span>
                </th>
                <th className="px-4 py-3 font-medium whitespace-nowrap">
                  <span className="flex items-center gap-1"><Star className="w-3 h-3" />Подходит</span>
                </th>
                <th className="px-4 py-3 font-medium whitespace-nowrap">Ниша</th>
                <th className="px-4 py-3 font-medium whitespace-nowrap">Статус</th>
                <th className="px-4 py-3 font-medium whitespace-nowrap">Последнее</th>
                <th className="px-3 py-3 font-medium w-24"></th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={10} className="px-4 py-10 text-center text-muted">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto" />
                  </td>
                </tr>
              )}
              {!isLoading && leads.length === 0 && (
                <tr>
                  <td colSpan={10} className="px-4 py-10 text-center text-muted">Лиды не найдены</td>
                </tr>
              )}
              {leads.map(lead => (
                <tr
                  key={lead.id}
                  className={clsx(
                    'border-b border-border/40 transition-colors',
                    selectedIds.has(lead.id) ? 'bg-accent/5' : 'hover:bg-white/3'
                  )}
                  onMouseEnter={() => setHoverRow(lead.id)}
                  onMouseLeave={() => setHoverRow(null)}
                >
                  <td className="px-3 py-3">
                    <button onClick={() => toggleOne(lead.id)} className="text-muted hover:text-white transition-colors">
                      {selectedIds.has(lead.id)
                        ? <CheckSquare className="w-4 h-4 text-accent" />
                        : <Square className="w-4 h-4" />}
                    </button>
                  </td>
                  <td className="px-4 py-3 max-w-xs">
                    <Link to={`/leads/${lead.id}`} className="hover:text-accent transition-colors block">
                      <div className="font-medium whitespace-nowrap">{lead.full_name || `#${lead.id}`}</div>
                    </Link>
                    <div className="flex items-center gap-1 mt-0.5">
                      {lead.username && <span className="text-xs text-muted">@{lead.username}</span>}
                      <button
                        title="Написать лиду"
                        onClick={e => { e.preventDefault(); writeMutation.mutate(lead) }}
                        disabled={writeMutation.isPending}
                        className="p-0.5 rounded text-muted hover:text-green-400 hover:bg-green-500/10 transition-colors"
                      >
                        <MessageSquare className="w-3 h-3" />
                      </button>
                      <button
                        title="Это спам"
                        onClick={e => { e.preventDefault(); spamMutation.mutate(lead) }}
                        disabled={spamMutation.isPending}
                        className="p-0.5 rounded text-muted hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      >
                        <Ban className="w-3 h-3" />
                      </button>
                    </div>
                    {lead.vacancy_text && (
                      <div className="text-xs text-white/40 mt-1 max-w-[320px] leading-relaxed">
                        {lead.vacancy_text}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {hoverRow === lead.id
                      ? <QuickTierButtons leadId={lead.id} currentTier={lead.tier} onDone={() => setHoverRow(null)} />
                      : <TierBadge tier={lead.tier} />}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <div className="w-14 h-1.5 bg-border rounded-full overflow-hidden">
                        <div
                          className={clsx('h-full rounded-full', lead.lead_score >= 70 ? 'bg-red-500' : lead.lead_score >= 40 ? 'bg-amber-500' : 'bg-indigo-500')}
                          style={{ width: `${Math.min(100, Math.max(0, lead.lead_score))}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted font-mono">{lead.lead_score.toFixed(0)}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3"><StarRating value={lead.qual_score} /></td>
                  <td className="px-4 py-3"><StarRating value={lead.fit_score} /></td>
                  <td className="px-4 py-3 text-muted text-xs whitespace-nowrap max-w-[120px] truncate">{lead.niche || '—'}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      lead.status === 'qualified' ? 'bg-green-500/20 text-green-400' :
                      lead.status === 'contacted' ? 'bg-blue-500/20 text-blue-400' :
                      lead.status === 'lost' ? 'bg-red-500/20 text-red-400' :
                      'bg-border text-muted'
                    }`}>{lead.status}</span>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted whitespace-nowrap">
                    {lead.last_interaction
                      ? formatDistanceToNow(new Date(lead.last_interaction), { addSuffix: true, locale: ru })
                      : '—'}
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex items-center gap-0.5 justify-end">
                      <Link to={`/leads/${lead.id}`} className="p-1.5 rounded text-muted hover:text-white transition-colors text-xs">→</Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Spam toast */}
      {spamToast && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-950/90 border border-red-500/40 text-white text-sm shadow-lg">
          <Ban className="w-4 h-4 text-red-400 shrink-0" />
          <span>Заблокировано: {spamToast}</span>
          <button onClick={() => setSpamToast(null)} className="ml-2 text-white/50 hover:text-white"><X className="w-3.5 h-3.5" /></button>
        </div>
      )}

      {/* Draft modal */}
      {draftModal && (
        <DraftModal
          lead={draftModal.lead}
          draft={draftModal.draft}
          onClose={() => setDraftModal(null)}
        />
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-sm text-muted">
            {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} из {total}
          </span>
          <div className="flex gap-2">
            <button className="btn-ghost" disabled={page === 0} onClick={() => setPage(p => p - 1)}>
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs text-muted self-center px-2">{page + 1} / {totalPages}</span>
            <button className="btn-ghost" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
