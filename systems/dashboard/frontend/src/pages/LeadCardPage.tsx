import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { leadsApi, dialogsApi } from '../api/client'
import { Lead } from '../types'
import { ArrowLeft, RefreshCw, Archive, MessageSquare, Clock } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'

const TIER_OPTIONS = ['HOT', 'WARM', 'COLD']
const STATUS_OPTIONS = ['new', 'contacted', 'qualified', 'lost']

export default function LeadCardPage() {
  const { id } = useParams<{ id: string }>()
  const leadId = Number(id)
  const qc = useQueryClient()
  const navigate = useNavigate()

  const { data: lead, isLoading } = useQuery<Lead>({
    queryKey: ['lead', leadId],
    queryFn: () => leadsApi.get(leadId).then(r => r.data),
  })

  const { data: history } = useQuery({
    queryKey: ['lead-history', leadId],
    queryFn: () => leadsApi.history(leadId).then(r => r.data),
  })

  const patch = useMutation({
    mutationFn: (data: Record<string, unknown>) => leadsApi.patch(leadId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['lead', leadId] }),
  })

  const reprocess = useMutation({
    mutationFn: () => leadsApi.reprocess(leadId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['lead', leadId] }),
  })

  const archive = useMutation({
    mutationFn: () => leadsApi.archive(leadId),
    onSuccess: () => navigate('/leads'),
  })

  const startDialog = useMutation({
    mutationFn: () => dialogsApi.start(leadId),
    onSuccess: (res) => navigate(`/dialogs/${res.data.id}`),
  })

  const [niche, setNiche] = useState('')
  const [source, setSource] = useState('')

  if (isLoading) return (
    <div className="p-6 flex justify-center">
      <RefreshCw className="w-6 h-6 animate-spin text-muted" />
    </div>
  )
  if (!lead) return <div className="p-6 text-muted">Лид не найден</div>

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Link to="/leads" className="btn-ghost p-2">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-semibold">{lead.full_name || `Lead #${lead.id}`}</h1>
          {lead.username && <p className="text-sm text-muted">@{lead.username}</p>}
        </div>
        <div className="flex gap-2">
          <button
            className="btn-ghost flex items-center gap-1.5 text-sm"
            onClick={() => startDialog.mutate()}
            disabled={startDialog.isPending}
          >
            <MessageSquare className="w-4 h-4" /> Диалог
          </button>
          <button
            className="btn-ghost flex items-center gap-1.5 text-sm"
            onClick={() => reprocess.mutate()}
            disabled={reprocess.isPending}
          >
            <RefreshCw className={`w-4 h-4 ${reprocess.isPending ? 'animate-spin' : ''}`} />
            Перезапуск
          </button>
          <button
            className="btn-ghost flex items-center gap-1.5 text-sm text-red-400 hover:text-red-300"
            onClick={() => { if (confirm('Архивировать лид?')) archive.mutate() }}
          >
            <Archive className="w-4 h-4" /> Архив
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        {/* Main info */}
        <div className="card space-y-3">
          <h2 className="font-medium text-sm text-muted uppercase tracking-wide">Основное</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-muted text-xs mb-1">Telegram ID</p>
              <p>{lead.telegram_id}</p>
            </div>
            <div>
              <p className="text-muted text-xs mb-1">Скор</p>
              <p className="font-mono">{lead.lead_score.toFixed(1)}</p>
            </div>
            <div>
              <p className="text-muted text-xs mb-1">Pipeline stage</p>
              <p>{lead.pipeline_stage}</p>
            </div>
            <div>
              <p className="text-muted text-xs mb-1">Приоритет</p>
              <p>{lead.priority}</p>
            </div>
          </div>
          {lead.last_interaction && (
            <div className="flex items-center gap-1.5 text-xs text-muted">
              <Clock className="w-3.5 h-3.5" />
              {formatDistanceToNow(new Date(lead.last_interaction), { addSuffix: true, locale: ru })}
            </div>
          )}
        </div>

        {/* Editable fields */}
        <div className="card space-y-3">
          <h2 className="font-medium text-sm text-muted uppercase tracking-wide">Редактирование</h2>
          <div className="space-y-2">
            <div>
              <label className="text-xs text-muted mb-1 block">Тир</label>
              <div className="flex gap-1.5">
                {TIER_OPTIONS.map(t => (
                  <button
                    key={t}
                    onClick={() => patch.mutate({ tier: t })}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                      lead.tier === t
                        ? t === 'HOT' ? 'bg-red-500 text-white' : t === 'WARM' ? 'bg-amber-500 text-white' : 'bg-blue-500 text-white'
                        : 'bg-border text-muted hover:text-white'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs text-muted mb-1 block">Статус</label>
              <select
                className="input w-full text-xs"
                value={lead.status}
                onChange={e => patch.mutate({ status: e.target.value })}
              >
                {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="text-xs text-muted mb-1 block">Ниша</label>
                <input
                  className="input w-full text-xs"
                  placeholder={lead.niche ?? 'не задана'}
                  value={niche}
                  onChange={e => setNiche(e.target.value)}
                  onBlur={() => { if (niche) { patch.mutate({ niche }); setNiche('') }}}
                />
              </div>
              <div className="flex-1">
                <label className="text-xs text-muted mb-1 block">Источник</label>
                <input
                  className="input w-full text-xs"
                  placeholder={lead.source_channel ?? 'не задан'}
                  value={source}
                  onChange={e => setSource(e.target.value)}
                  onBlur={() => { if (source) { patch.mutate({ source_channel: source }); setSource('') }}}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Audit log */}
      <div className="card">
        <h2 className="font-medium text-sm text-muted uppercase tracking-wide mb-3">История изменений</h2>
        {!history || history.length === 0 ? (
          <p className="text-sm text-muted">Нет записей</p>
        ) : (
          <div className="space-y-2 max-h-60 overflow-auto">
            {history.map((entry: Record<string, unknown>) => (
              <div key={String(entry.id)} className="flex items-start gap-3 text-xs">
                <span className="text-muted shrink-0">{String(entry.ts).slice(0, 16)}</span>
                <span className="font-medium">{String(entry.action)}</span>
                {entry.new_value != null && (
                  <span className="text-muted font-mono">{String(entry.new_value).slice(0, 80)}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
