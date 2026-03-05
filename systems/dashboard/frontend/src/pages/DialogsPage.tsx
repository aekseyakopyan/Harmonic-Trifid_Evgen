import { useState, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { dialogsApi } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'
import { Dialog } from '../types'
import { MessageSquare, RefreshCw } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'
import clsx from 'clsx'

const STATUS_COLORS: Record<string, string> = {
  active: 'text-green-400',
  pending: 'text-amber-400',
  stopped: 'text-muted',
  completed: 'text-blue-400',
}

export default function DialogsPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['dialogs', statusFilter],
    queryFn: () =>
      dialogsApi.list({ status: statusFilter || undefined }).then(r => r.data),
  })

  useWebSocket('dialogs', useCallback(() => {
    qc.invalidateQueries({ queryKey: ['dialogs'] })
  }, [qc]))

  const dialogs: Dialog[] = data?.items ?? []
  const total = data?.total ?? 0

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold">Диалоги</h1>
          <p className="text-sm text-muted mt-0.5">Всего: {total}</p>
        </div>
        <select
          className="input"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
        >
          {['', 'active', 'pending', 'stopped', 'completed'].map(s => (
            <option key={s} value={s}>{s || 'Все статусы'}</option>
          ))}
        </select>
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-muted text-left">
              <th className="px-4 py-3 font-medium">Лид</th>
              <th className="px-4 py-3 font-medium">Канал</th>
              <th className="px-4 py-3 font-medium">Статус</th>
              <th className="px-4 py-3 font-medium">Режим</th>
              <th className="px-4 py-3 font-medium">Последнее сообщение</th>
              <th className="px-4 py-3 font-medium">Результат</th>
              <th className="px-4 py-3 font-medium w-16"></th>
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
            {!isLoading && dialogs.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-muted">Диалоги не найдены</td>
              </tr>
            )}
            {dialogs.map(dialog => (
              <tr key={dialog.id} className="border-b border-border/50 hover:bg-white/3 transition-colors">
                <td className="px-4 py-3">
                  <Link to={`/leads/${dialog.lead_id}`} className="hover:text-accent transition-colors">
                    <div className="font-medium">{dialog.full_name || `Lead #${dialog.lead_id}`}</div>
                    {dialog.username && <div className="text-xs text-muted">@{dialog.username}</div>}
                  </Link>
                </td>
                <td className="px-4 py-3 text-xs text-muted">{dialog.channel}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1.5">
                    <MessageSquare className={clsx('w-3.5 h-3.5', STATUS_COLORS[dialog.status] ?? 'text-muted')} />
                    <span className={clsx('text-xs', STATUS_COLORS[dialog.status] ?? 'text-muted')}>
                      {dialog.status}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-xs text-muted">
                  {dialog.auto_mode ? 'Авто' : 'Ручной'}
                </td>
                <td className="px-4 py-3 text-xs text-muted">
                  {dialog.last_message_at
                    ? formatDistanceToNow(new Date(dialog.last_message_at), { addSuffix: true, locale: ru })
                    : '—'}
                </td>
                <td className="px-4 py-3 text-xs text-muted">{dialog.result || '—'}</td>
                <td className="px-4 py-3">
                  <Link to={`/dialogs/${dialog.id}`} className="btn-ghost py-1 px-2 text-xs">→</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
