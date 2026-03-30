import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { leadsApi, dialogsApi } from '../api/client'
import { Lead } from '../types'
import { ArrowLeft, RefreshCw, Archive, MessageSquare, Clock, FileText, ExternalLink, Send } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'

function ScoreButtons({ label, value, onChange }: { label: string; value: number | null; onChange: (v: number) => void }) {
  return (
    <div>
      <label className="text-xs text-muted mb-1 block">{label}</label>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map(n => (
          <button
            key={n}
            onClick={() => onChange(n)}
            className={`w-8 h-8 rounded text-xs font-bold transition-colors ${
              value === n
                ? n >= 4 ? 'bg-green-500 text-white' : n === 3 ? 'bg-amber-500 text-white' : 'bg-red-500 text-white'
                : 'bg-border text-muted hover:text-white'
            }`}
          >
            {n}
          </button>
        ))}
        {value != null && (
          <button onClick={() => onChange(0)} className="w-8 h-8 rounded text-xs text-muted hover:text-white bg-border">✕</button>
        )}
      </div>
    </div>
  )
}

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

  const { data: vacancies } = useQuery({
    queryKey: ['lead-vacancies', leadId],
    queryFn: () => leadsApi.vacancies(leadId).then(r => r.data),
  })

  const { data: dialogsData } = useQuery({
    queryKey: ['lead-dialogs', leadId],
    queryFn: () => dialogsApi.list({ lead_id: leadId, limit: 3 }).then(r => r.data),
  })

  const latestDialogId = dialogsData?.items?.[0]?.id
  const { data: dialogDetail } = useQuery({
    queryKey: ['dialog', latestDialogId],
    queryFn: () => dialogsApi.get(latestDialogId!).then(r => r.data),
    enabled: !!latestDialogId,
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
  const [qualNotes, setQualNotes] = useState('')

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
          {lead.username && (
            <div className="flex items-center gap-2">
              <p className="text-sm text-muted">@{lead.username}</p>
              <a
                href={`tg://resolve?domain=${lead.username}`}
                className="inline-flex items-center gap-1 text-xs text-accent hover:text-white transition-colors"
                title="Открыть в Telegram"
              >
                <Send className="w-3 h-3" /> TG
              </a>
            </div>
          )}
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

      {/* Original vacancy texts */}
      {vacancies && vacancies.length > 0 && (
        <div className="card mb-4 space-y-3">
          <h2 className="font-medium text-sm text-muted uppercase tracking-wide flex items-center gap-2">
            <FileText className="w-4 h-4" /> Оригинальные сообщения ({vacancies.length})
          </h2>
          <div className="space-y-3">
            {vacancies.map((v: { id: number; text: string; source_channel: string; created_at: string; status: string }) => (
              <div key={v.id} className="bg-surface rounded-lg p-3 text-sm">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {v.source_channel && (
                      <span className="text-xs text-accent flex items-center gap-1">
                        <ExternalLink className="w-3 h-3" />{v.source_channel}
                      </span>
                    )}
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      v.status === 'accepted' ? 'bg-green-500/20 text-green-400' : 'bg-border text-muted'
                    }`}>{v.status}</span>
                  </div>
                  <span className="text-xs text-muted">{v.created_at?.slice(0, 16)}</span>
                </div>
                <p className="text-xs text-muted/90 whitespace-pre-wrap leading-relaxed">{v.text}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Qualification scoring */}
      <div className="card mb-4 space-y-4">
        <h2 className="font-medium text-sm text-muted uppercase tracking-wide">Оценка лида</h2>
        <div className="grid grid-cols-2 gap-4">
          <ScoreButtons
            label="Насколько лид целевой (1-5)"
            value={lead.qual_score}
            onChange={v => patch.mutate({ qual_score: v === 0 ? null : v })}
          />
          <ScoreButtons
            label="Насколько нам подходит (1-5)"
            value={lead.fit_score}
            onChange={v => patch.mutate({ fit_score: v === 0 ? null : v })}
          />
        </div>
        <div>
          <label className="text-xs text-muted mb-1 block">Заметки</label>
          <textarea
            className="input w-full text-xs min-h-[60px] resize-y"
            placeholder={lead.qual_notes ?? 'Добавьте заметку по лиду...'}
            value={qualNotes}
            onChange={e => setQualNotes(e.target.value)}
            onBlur={() => {
              if (qualNotes !== '') {
                patch.mutate({ qual_notes: qualNotes })
                setQualNotes('')
              }
            }}
          />
          {lead.qual_notes && !qualNotes && (
            <p className="text-xs text-muted mt-1 px-1">{lead.qual_notes}</p>
          )}
        </div>
        {(lead.qual_score != null || lead.fit_score != null) && (
          <div className="flex gap-3 text-xs">
            {lead.qual_score != null && (
              <span className={`px-2 py-0.5 rounded font-medium ${
                lead.qual_score >= 4 ? 'bg-green-500/20 text-green-400' :
                lead.qual_score === 3 ? 'bg-amber-500/20 text-amber-400' :
                'bg-red-500/20 text-red-400'
              }`}>
                Целевой: {lead.qual_score}/5
              </span>
            )}
            {lead.fit_score != null && (
              <span className={`px-2 py-0.5 rounded font-medium ${
                lead.fit_score >= 4 ? 'bg-green-500/20 text-green-400' :
                lead.fit_score === 3 ? 'bg-amber-500/20 text-amber-400' :
                'bg-red-500/20 text-red-400'
              }`}>
                Подходит: {lead.fit_score}/5
              </span>
            )}
          </div>
        )}
      </div>

      {/* Dialog history preview */}
      {dialogDetail && dialogDetail.messages?.length > 0 && (
        <div className="card mb-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-medium text-sm text-muted uppercase tracking-wide flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              Последний диалог
              <span className={`px-1.5 py-0.5 rounded text-xs ml-1 ${
                dialogDetail.dialog?.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-border text-muted'
              }`}>{dialogDetail.dialog?.status}</span>
            </h2>
            <Link to={`/dialogs/${latestDialogId}`} className="text-xs text-accent hover:text-white">
              Открыть →
            </Link>
          </div>
          <div className="space-y-2 max-h-56 overflow-auto">
            {dialogDetail.messages.slice(-5).map((msg: { id: number; role: string; content: string; sent_at: string; is_manual: number }) => (
              <div key={msg.id} className={`flex gap-2 text-xs ${msg.role === 'assistant' ? 'flex-row-reverse' : ''}`}>
                <div className={`max-w-[80%] rounded-lg px-3 py-2 ${
                  msg.role === 'assistant'
                    ? 'bg-accent/20 text-white'
                    : 'bg-surface text-white/80'
                }`}>
                  <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  <p className="text-muted mt-1 text-[10px]">{msg.sent_at?.slice(11, 16)} {msg.is_manual ? '✏️' : '🤖'}</p>
                </div>
              </div>
            ))}
          </div>
          {dialogsData && dialogsData.items?.length > 1 && (
            <p className="text-xs text-muted">Всего диалогов: {dialogsData.items.length}</p>
          )}
        </div>
      )}

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
