import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { promptsApi } from '../api/client'
import { Prompt, PromptVersion } from '../types'
import { ArrowLeft, Save, RotateCcw, Clock } from 'lucide-react'

const STAGE_OPTIONS = ['filter', 'scorer', 'llm', 'outreach', 'dialog', 'other']

export default function PromptEditorPage() {
  const { id } = useParams<{ id: string }>()
  const isNew = !id || id === 'new'
  const promptId = isNew ? null : Number(id)
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [name, setName] = useState('')
  const [stage, setStage] = useState('llm')
  const [content, setContent] = useState('')
  const [showVersions, setShowVersions] = useState(false)

  const { data: prompt } = useQuery<Prompt>({
    queryKey: ['prompt', promptId],
    queryFn: () => promptsApi.get(promptId!).then(r => r.data),
    enabled: !isNew,
  })

  const { data: versions } = useQuery<PromptVersion[]>({
    queryKey: ['prompt-versions', promptId],
    queryFn: () => promptsApi.versions(promptId!).then(r => r.data),
    enabled: !isNew && showVersions,
  })

  useEffect(() => {
    if (prompt) {
      setName(prompt.name)
      setStage(prompt.stage)
      setContent(prompt.content)
    }
  }, [prompt])

  const create = useMutation({
    mutationFn: () => promptsApi.create({ name, stage, content }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['prompts'] })
      navigate(`/prompts/${res.data.id}`)
    },
  })

  const update = useMutation({
    mutationFn: () => promptsApi.update(promptId!, { name, stage, content }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['prompts'] })
      qc.invalidateQueries({ queryKey: ['prompt', promptId] })
    },
  })

  const rollback = useMutation({
    mutationFn: (version: number) => promptsApi.rollback(promptId!, version),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['prompt', promptId] })
      setShowVersions(false)
    },
  })

  const handleSave = () => {
    if (isNew) create.mutate()
    else update.mutate()
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-border">
        <Link to="/prompts" className="btn-ghost p-2">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="flex-1">
          <h1 className="text-base font-semibold">
            {isNew ? 'Новый промпт' : `Редактирование: ${prompt?.name}`}
          </h1>
          {!isNew && prompt && (
            <p className="text-xs text-muted">v{prompt.version} · {prompt.stage}</p>
          )}
        </div>
        <div className="flex gap-2">
          {!isNew && (
            <button
              className="btn-ghost flex items-center gap-1.5 text-sm"
              onClick={() => setShowVersions(!showVersions)}
            >
              <Clock className="w-4 h-4" /> История
            </button>
          )}
          <button
            className="btn-primary flex items-center gap-1.5"
            onClick={handleSave}
            disabled={create.isPending || update.isPending || !name || !content}
          >
            <Save className="w-4 h-4" />
            {isNew ? 'Создать' : 'Сохранить'}
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Editor */}
        <div className="flex-1 flex flex-col p-4 gap-3 overflow-auto">
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-xs text-muted block mb-1">Название</label>
              <input
                className="input w-full"
                placeholder="Название промпта"
                value={name}
                onChange={e => setName(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-muted block mb-1">Стадия</label>
              <select className="input" value={stage} onChange={e => setStage(e.target.value)}>
                {STAGE_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <div className="flex-1">
            <label className="text-xs text-muted block mb-1">Контент</label>
            <textarea
              className="input w-full h-full min-h-64 resize-none font-mono text-xs leading-relaxed"
              placeholder="Введите промпт..."
              value={content}
              onChange={e => setContent(e.target.value)}
            />
          </div>
          <div className="text-xs text-muted">
            {content.length} символов · {content.split(/\s+/).filter(Boolean).length} слов
          </div>
        </div>

        {/* Versions panel */}
        {showVersions && !isNew && (
          <div className="w-64 border-l border-border p-4 overflow-auto">
            <h3 className="text-sm font-medium mb-3">История версий</h3>
            {!versions && <p className="text-xs text-muted">Загрузка...</p>}
            {versions?.map(v => (
              <div key={v.id} className="mb-3 p-2 border border-border rounded-lg">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium">v{v.version}</span>
                  <button
                    className="btn-ghost py-0.5 px-2 text-xs flex items-center gap-1"
                    onClick={() => {
                      if (confirm(`Откатить до v${v.version}?`)) rollback.mutate(v.version)
                    }}
                  >
                    <RotateCcw className="w-3 h-3" /> Откат
                  </button>
                </div>
                <p className="text-xs text-muted">{v.created_at.slice(0, 16)}</p>
                <p className="text-xs text-muted mt-1 line-clamp-3">{v.content.slice(0, 80)}...</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
