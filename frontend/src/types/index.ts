export interface UserInfo {
  username: string
  userId: string
  token: string
}

export interface TaskItem {
  id: string
  task_name: string
  source_type: string
  status: string
  status_text: string
  submitter: string
  created_at: string
  updated_at: string
  error?: string
}

export interface TestCase {
  id: number
  module: string
  title: string
  precondition: string
  steps: string
  expected_result: string
  priority: '高' | '中' | '低'
  adoption_status?: 'accepted' | 'rejected'
}

export interface ReviewResult {
  issues: string[]
  suggestions: string[]
  missing_scenarios: Array<{
    module: string
    scenario: string
    test_point: string
  }>
  quality_score: number
  summary: string
  reviewed_cases?: TestCase[]
}

export interface TaskPhase {
  status: 'pending' | 'running' | 'completed' | 'failed'
  label: string
  data: Record<string, unknown> | null
}

export interface TaskDetail {
  id: string
  task_name: string
  status: string
  error: string | null
  mindmap: unknown
  phases: {
    analysis: TaskPhase
    generation: TaskPhase
    review: TaskPhase
  }
}

export interface AIModelConfig {
  id: string
  name: string
  model_type: string
  api_key: string
  api_base_url: string
  model_name: string
  max_tokens: number
  temperature: number
  top_p: number
  enabled: boolean
  created_at: string
  updated_at: string
  creator: string
  modifier: string
}

export interface PromptConfigItem {
  id: string
  name: string
  role: string
  prompt_type?: string
  content: string
  enabled: boolean
  created_at: string
  updated_at: string
  creator: string
}

export interface GenerationBehaviorConfigItem {
  id: string
  name: string
  output_mode: string
  enable_ai_review: boolean
  review_timeout_seconds: number
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface NotifyChannelConfig {
  name: string
  enabled: boolean
  webhook: string
  secret: string
  custom_keyword: string
}

export interface ApiResponse<T = unknown> {
  code: number
  msg: string
  data: T
  tid: string
  ts: number
}
