export interface Lead {
  id: number
  telegram_id: number
  username: string | null
  full_name: string | null
  lead_score: number
  tier: 'HOT' | 'WARM' | 'COLD' | null
  priority: number
  pipeline_stage: number
  niche: string | null
  source_channel: string | null
  status: string
  is_archived: number
  last_interaction: string | null
  created_at: string | null
  updated_at: string | null
}

export interface Dialog {
  id: number
  lead_id: number
  channel: string
  target_user: string | null
  status: string
  auto_mode: number
  last_message_at: string | null
  started_at: string | null
  ended_at: string | null
  result: string | null
  notes: string | null
  username?: string | null
  full_name?: string | null
}

export interface DialogMessage {
  id: number
  dialog_id: number
  role: string
  content: string
  sent_at: string
  is_manual: number
}

export interface PipelineConfigItem {
  key: string
  value: string
  updated_at: string | null
}

export interface BlacklistEntry {
  id: number
  type: string
  value: string
  added_at: string
}

export interface Prompt {
  id: number
  name: string
  stage: string
  content: string
  version: number
  is_active: number
  created_at: string
}

export interface PromptVersion {
  id: number
  prompt_id: number
  version: number
  content: string
  created_at: string
}

export interface AnalyticsOverview {
  period: string
  total_leads: number
  new_leads: number
  hot_leads: number
  warm_leads: number
  dialogs_active: number
  dialogs_in_period: number
  messages_in_period: number
  conversion_rate: number
}
