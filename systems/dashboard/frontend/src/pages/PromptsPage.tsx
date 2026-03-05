import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { promptsApi } from '../api/client'
import { Prompt } from '../types'
import { Plus, Edit2, ToggleLeft, ToggleRight } from 'lucide-react'

const STAGE_COLORS: Record<string, string> = {
  filter: 'bg-red-500/20 text-red-400',
  scorer: 'bg-amber-500/20 text-amber-400',
  llm: 'bg-purple-500/20 text-purple-400',
  outreach: 'bg-green-500/20 text-green-400',
  dialog: 'bg-blue-500/20 text-blue-400',
}

export default function PromptsPage() {
  const qc = useQueryClient()

  const { data: prompts = [] } = useQuery({
    queryKey: ['prompts'],
    queryFn: () => promptsApi.list().then(r => r.data as Prompt[]),
  })

  const toggle = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: number }) =>
      promptsApi.update(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['prompts'] }),
  })

  const grouped = prompts.reduce<Record<string, Prompt[]>>((acc, p) => {
    if (!acc[p.stage]) acc[p.stage] = []
    acc[p.stage].push(p)
    return acc
  }, {})

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Промпты</h1>
        <Link to="/prompts/new" className="btn-primary flex items-center gap-1.5">
          <Plus className="w-4 h-4" /> Новый промпт
        </Link>
      </div>

      {Object.entries(grouped).map(([stage, items]) => (
        <div key={stage} className="mb-6">
          <h2 className="text-sm font-medium text-muted uppercase tracking-wide mb-3">
            {stage} ({items.length})
          </h2>
          <div className="space-y-2">
            {items.map(prompt => (
              <div
                key={prompt.id}
                className={`card flex items-center gap-3 ${!prompt.is_active ? 'opacity-50' : ''}`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${STAGE_COLORS[stage] ?? 'bg-border text-muted'}`}>
                      {stage}
                    </span>
                    <span className="font-medium text-sm">{prompt.name}</span>
                    <span className="text-xs text-muted">v{prompt.version}</span>
                  </div>
                  <p className="text-xs text-muted mt-1 truncate">
                    {prompt.content.slice(0, 120)}...
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => toggle.mutate({ id: prompt.id, is_active: prompt.is_active ? 0 : 1 })}
                    className="btn-ghost p-1.5"
                    title={prompt.is_active ? 'Деактивировать' : 'Активировать'}
                  >
                    {prompt.is_active
                      ? <ToggleRight className="w-5 h-5 text-accent" />
                      : <ToggleLeft className="w-5 h-5 text-muted" />}
                  </button>
                  <Link to={`/prompts/${prompt.id}`} className="btn-ghost p-1.5">
                    <Edit2 className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {prompts.length === 0 && (
        <div className="text-center py-12 text-muted">
          <p>Промпты не созданы</p>
          <Link to="/prompts/new" className="btn-primary inline-flex items-center gap-1.5 mt-4">
            <Plus className="w-4 h-4" /> Создать первый промпт
          </Link>
        </div>
      )}
    </div>
  )
}
