import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { pipelineApi } from '../api/client'
import { PipelineConfigItem, BlacklistEntry } from '../types'
import { Save, Plus, Trash2, RefreshCw } from 'lucide-react'

const CONFIG_LABELS: Record<string, string> = {
  heuristic_hot_threshold: 'Порог HOT (эвристика)',
  heuristic_warm_threshold: 'Порог WARM (эвристика)',
  ml_min_score: 'Мин. скор ML',
  llm_enabled: 'LLM включён (1/0)',
  dedup_window_hours: 'Окно дедупликации (ч)',
  stages_enabled: 'Включённые стадии (JSON)',
}

const BLACKLIST_TYPES = ['word', 'channel', 'niche']

export default function PipelineConfigPage() {
  const qc = useQueryClient()
  const [newBLType, setNewBLType] = useState('word')
  const [newBLValues, setNewBLValues] = useState('')
  const [editValues, setEditValues] = useState<Record<string, string>>({})

  const { data: config, isLoading: configLoading } = useQuery({
    queryKey: ['pipeline-config'],
    queryFn: () => pipelineApi.config().then(r => r.data as PipelineConfigItem[]),
  })

  const { data: blacklist } = useQuery({
    queryKey: ['pipeline-blacklist'],
    queryFn: () => pipelineApi.blacklist().then(r => r.data as BlacklistEntry[]),
  })

  const { data: stats } = useQuery({
    queryKey: ['pipeline-stats'],
    queryFn: () => pipelineApi.stats().then(r => r.data),
  })

  const patchConfig = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      pipelineApi.patchConfig(key, value),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline-config'] }),
  })

  const addBL = useMutation({
    mutationFn: () => {
      const values = newBLValues.split('\n').map(v => v.trim()).filter(Boolean)
      return pipelineApi.addBlacklist(newBLType, values)
    },
    onSuccess: () => {
      setNewBLValues('')
      qc.invalidateQueries({ queryKey: ['pipeline-blacklist'] })
    },
  })

  const removeBL = useMutation({
    mutationFn: ({ type, value }: { type: string; value: string }) =>
      pipelineApi.removeBlacklist(type, [value]),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline-blacklist'] }),
  })

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <h1 className="text-xl font-semibold">Pipeline Config</h1>

      <div className="grid grid-cols-2 gap-4">
        {/* Stats */}
        <div className="card space-y-3">
          <h2 className="font-medium text-sm text-muted uppercase tracking-wide">Статистика</h2>
          {stats && (
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="card bg-surface">
                <p className="text-muted text-xs">Всего лидов</p>
                <p className="text-2xl font-bold mt-1">{stats.total}</p>
              </div>
              <div className="card bg-surface">
                <p className="text-muted text-xs">В архиве</p>
                <p className="text-2xl font-bold mt-1">{stats.archived}</p>
              </div>
              {stats.by_tier?.map((t: { tier: string; cnt: number }) => (
                <div key={t.tier} className="card bg-surface">
                  <p className="text-muted text-xs">{t.tier}</p>
                  <p className="text-xl font-bold mt-1">{t.cnt}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Config params */}
        <div className="card space-y-3">
          <h2 className="font-medium text-sm text-muted uppercase tracking-wide">Параметры</h2>
          {configLoading && <RefreshCw className="w-5 h-5 animate-spin text-muted" />}
          {config?.map(item => (
            <div key={item.key} className="flex items-center gap-2">
              <label className="text-xs text-muted flex-1">
                {CONFIG_LABELS[item.key] ?? item.key}
              </label>
              <input
                className="input w-40 text-xs"
                value={editValues[item.key] ?? item.value}
                onChange={e => setEditValues(prev => ({ ...prev, [item.key]: e.target.value }))}
                onBlur={() => {
                  const val = editValues[item.key]
                  if (val !== undefined && val !== item.value) {
                    patchConfig.mutate({ key: item.key, value: val })
                  }
                }}
              />
              <button
                className="btn-ghost p-1.5"
                onClick={() => {
                  const val = editValues[item.key]
                  if (val !== undefined) patchConfig.mutate({ key: item.key, value: val })
                }}
              >
                <Save className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Blacklist */}
      <div className="card space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-medium text-sm text-muted uppercase tracking-wide">Чёрный список</h2>
          <span className="text-xs text-muted">{blacklist?.length ?? 0} записей</span>
        </div>

        {/* Add form */}
        <div className="flex gap-2 items-end">
          <div>
            <label className="text-xs text-muted block mb-1">Тип</label>
            <select className="input text-xs" value={newBLType} onChange={e => setNewBLType(e.target.value)}>
              {BLACKLIST_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="flex-1">
            <label className="text-xs text-muted block mb-1">Значения (по одному на строку)</label>
            <textarea
              className="input w-full text-xs resize-none"
              rows={2}
              placeholder="word1&#10;word2"
              value={newBLValues}
              onChange={e => setNewBLValues(e.target.value)}
            />
          </div>
          <button className="btn-primary flex items-center gap-1.5" onClick={() => addBL.mutate()}>
            <Plus className="w-4 h-4" /> Добавить
          </button>
        </div>

        {/* Grouped list */}
        <div className="space-y-3">
          {BLACKLIST_TYPES.map(type => {
            const entries = blacklist?.filter(e => e.type === type) ?? []
            if (entries.length === 0) return null
            return (
              <div key={type}>
                <p className="text-xs font-medium text-muted mb-2 uppercase">{type}s ({entries.length})</p>
                <div className="flex flex-wrap gap-1.5">
                  {entries.map(entry => (
                    <span
                      key={entry.id}
                      className="flex items-center gap-1 bg-border px-2 py-0.5 rounded text-xs"
                    >
                      {entry.value}
                      <button
                        onClick={() => removeBL.mutate({ type: entry.type, value: entry.value })}
                        className="text-muted hover:text-red-400 ml-0.5"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
