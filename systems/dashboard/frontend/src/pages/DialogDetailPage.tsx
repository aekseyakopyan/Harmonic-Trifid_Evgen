import { useState, useRef, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dialogsApi } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'
import { Dialog, DialogMessage } from '../types'
import { ArrowLeft, Send, Square, Bot, User, RefreshCw } from 'lucide-react'
import clsx from 'clsx'

export default function DialogDetailPage() {
  const { id } = useParams<{ id: string }>()
  const dialogId = Number(id)
  const qc = useQueryClient()
  const [message, setMessage] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['dialog', dialogId],
    queryFn: () => dialogsApi.get(dialogId).then(r => r.data),
  })

  useWebSocket('dialogs', useCallback((event: unknown) => {
    const e = event as { event?: string; dialog_id?: number }
    if (e?.dialog_id === dialogId || e?.event === 'dialog_stopped') {
      qc.invalidateQueries({ queryKey: ['dialog', dialogId] })
    }
  }, [dialogId, qc]))

  const stop = useMutation({
    mutationFn: () => dialogsApi.stop(dialogId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dialog', dialogId] }),
  })

  const toggleAuto = useMutation({
    mutationFn: (autoMode: number) => dialogsApi.patch(dialogId, { auto_mode: autoMode }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dialog', dialogId] }),
  })

  const send = useMutation({
    mutationFn: (content: string) => dialogsApi.sendMessage(dialogId, content),
    onSuccess: () => {
      setMessage('')
      qc.invalidateQueries({ queryKey: ['dialog', dialogId] })
    },
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [data?.messages])

  if (isLoading) return (
    <div className="p-6 flex justify-center">
      <RefreshCw className="w-6 h-6 animate-spin text-muted" />
    </div>
  )

  const dialog: Dialog = data?.dialog
  const messages: DialogMessage[] = data?.messages ?? []

  if (!dialog) return <div className="p-6 text-muted">Диалог не найден</div>

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-border">
        <Link to="/dialogs" className="btn-ghost p-2">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="flex-1">
          <h1 className="text-base font-semibold">
            Диалог #{dialogId} —{' '}
            <Link to={`/leads/${dialog.lead_id}`} className="text-accent hover:underline">
              {dialog.full_name || `Lead #${dialog.lead_id}`}
            </Link>
          </h1>
          <p className="text-xs text-muted">{dialog.channel} · {dialog.status}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            className={clsx(
              'px-3 py-1.5 rounded text-xs font-medium transition-colors',
              dialog.auto_mode
                ? 'bg-accent/20 text-accent hover:bg-accent/30'
                : 'bg-border text-muted hover:text-white'
            )}
            onClick={() => toggleAuto.mutate(dialog.auto_mode ? 0 : 1)}
          >
            {dialog.auto_mode ? '🤖 Авто' : '👤 Ручной'}
          </button>
          {dialog.status === 'active' && (
            <button
              className="btn-ghost text-red-400 hover:text-red-300 flex items-center gap-1.5 text-sm"
              onClick={() => stop.mutate()}
            >
              <Square className="w-3.5 h-3.5" /> Стоп
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto p-4 space-y-3">
        {messages.length === 0 && (
          <p className="text-center text-muted text-sm py-8">Нет сообщений</p>
        )}
        {messages.map(msg => (
          <div
            key={msg.id}
            className={clsx(
              'flex gap-2 max-w-2xl',
              msg.role === 'assistant' ? 'ml-auto flex-row-reverse' : ''
            )}
          >
            <div className={clsx(
              'w-7 h-7 rounded-full flex items-center justify-center shrink-0',
              msg.role === 'assistant' ? 'bg-accent/20' : 'bg-border'
            )}>
              {msg.role === 'assistant'
                ? <Bot className="w-4 h-4 text-accent" />
                : <User className="w-4 h-4 text-muted" />}
            </div>
            <div className={clsx(
              'px-3 py-2 rounded-lg text-sm max-w-lg',
              msg.role === 'assistant'
                ? 'bg-accent/10 text-white border border-accent/20'
                : 'bg-card border border-border text-white'
            )}>
              <p className="whitespace-pre-wrap">{msg.content}</p>
              <p className="text-xs text-muted mt-1">
                {msg.sent_at.slice(0, 16)}
                {msg.is_manual ? ' · ручное' : ''}
              </p>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      {dialog.status === 'active' && (
        <div className="p-4 border-t border-border">
          <div className="flex gap-2">
            <textarea
              className="input flex-1 resize-none text-sm"
              rows={2}
              placeholder="Написать сообщение вручную..."
              value={message}
              onChange={e => setMessage(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  if (message.trim()) send.mutate(message.trim())
                }
              }}
            />
            <button
              className="btn-primary self-end"
              disabled={!message.trim() || send.isPending}
              onClick={() => { if (message.trim()) send.mutate(message.trim()) }}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
