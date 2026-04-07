import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export default api

// Leads
export const leadsApi = {
  list: (params?: Record<string, unknown>) => api.get('/leads/', { params }),
  get: (id: number) => api.get(`/leads/${id}`),
  patch: (id: number, data: Record<string, unknown>) => api.patch(`/leads/${id}`, data),
  reprocess: (id: number) => api.post(`/leads/${id}/reprocess`),
  archive: (id: number) => api.post(`/leads/${id}/archive`),
  history: (id: number) => api.get(`/leads/${id}/history`),
  vacancies: (id: number) => api.get(`/leads/${id}/vacancies`),
  bulk: (lead_ids: number[], action: string, value = '') =>
    api.post('/leads/bulk', lead_ids, { params: { action, value } }),
  export: (params?: Record<string, unknown>) =>
    api.post('/leads/export', {}, { params, responseType: 'blob' }),
  draft: (id: number) => api.get<{ draft: string | null }>(`/leads/${id}/draft`),
  queueOutreach: (id: number) => api.post(`/leads/${id}/queue_outreach`),
  sendOutreach: (id: number) => api.post<{ ok: boolean; queued: boolean }>(`/leads/${id}/send_outreach`),
  generateDraft: (id: number) => api.post<{ draft: string }>(`/leads/${id}/generate_draft`),
  markSpam: (id: number) => api.post<{ ok: boolean; reason: string; username: string }>(`/leads/${id}/mark_spam`),
}

// Dialogs
export const dialogsApi = {
  list: (params?: Record<string, unknown>) => api.get('/dialogs/', { params }),
  get: (id: number) => api.get(`/dialogs/${id}`),
  start: (leadId: number, channel = 'telegram', targetUser?: string) =>
    api.post(`/dialogs/${leadId}/start`, {}, { params: { channel, target_user: targetUser } }),
  stop: (id: number) => api.post(`/dialogs/${id}/stop`),
  patch: (id: number, data: Record<string, unknown>) => api.patch(`/dialogs/${id}`, data),
  sendMessage: (id: number, content: string, role = 'assistant') =>
    api.post(`/dialogs/${id}/message`, { content, role }),
}

// Pipeline
export const pipelineApi = {
  config: () => api.get('/pipeline/config'),
  patchConfig: (key: string, value: string) => api.patch(`/pipeline/config/${key}`, { value }),
  blacklist: (type?: string) => api.get('/pipeline/blacklist', { params: { type } }),
  addBlacklist: (type: string, values: string[]) =>
    api.post('/pipeline/blacklist/words', { type, values }),
  removeBlacklist: (type: string, values: string[]) =>
    api.delete('/pipeline/blacklist/words', { data: { type, values } }),
  stats: () => api.get('/pipeline/stats'),
}

// Prompts
export const promptsApi = {
  list: () => api.get('/prompts/'),
  get: (id: number) => api.get(`/prompts/${id}`),
  create: (data: Record<string, unknown>) => api.post('/prompts/', data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/prompts/${id}`, data),
  rollback: (id: number, version: number) =>
    api.post(`/prompts/${id}/rollback`, {}, { params: { version } }),
  versions: (id: number) => api.get(`/prompts/${id}/versions`),
}

// Analytics
export const analyticsApi = {
  overview: (period = 'week') => api.get('/analytics/overview', { params: { period } }),
  timeline: (period = 'week') => api.get('/analytics/leads_timeline', { params: { period } }),
  byNiche: () => api.get('/analytics/by_niche'),
  bySource: () => api.get('/analytics/by_source'),
  alexeyLoad: () => api.get('/analytics/alexey_load'),
  funnel: () => api.get('/analytics/funnel'),
  qualDistribution: () => api.get('/analytics/qual_distribution'),
  qualTrend: (period = 'week') => api.get('/analytics/qual_trend', { params: { period } }),
  filterStats: () => api.get('/analytics/filter_stats'),
  home: () => api.get('/analytics/home'),
}
