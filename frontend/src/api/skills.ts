import request from '../utils/request'

export interface SkillSummary {
  skill_id: string
  name?: string
  description?: string
  version?: string
  lang?: string
  tags?: string[]
  primary_prompt_file?: string
  prompt_files?: string[]
  prompt_length?: number
  templates?: string[]
  examples?: { filename: string; kind: string; is_binary: boolean }[]
  references?: string[]
  overlays_applied?: string[]
  content_hash?: string
  error?: string
}

export interface RoleMappingItem {
  default_skill_id: string
  env_override: string
  effective_skill_id: string
}

export interface SkillsListResponse {
  enabled: boolean
  fewshot_enabled: boolean
  discover_enabled: boolean
  ab_enabled: boolean
  legacy_fallback_enabled: boolean
  prompt_token_budget: number
  library_dir: string
  active_overlays: string[]
  skills: SkillSummary[]
  role_mapping: Record<string, RoleMappingItem>
}

export async function listSkills(lang?: string) {
  const params = lang ? { lang } : undefined
  return request.get<SkillsListResponse>('/ai/skills', { params })
}

export async function getSkill(skillId: string) {
  return request.get(`/ai/skills/${encodeURIComponent(skillId)}`)
}

export async function reloadSkills() {
  return request.post('/ai/skills/reload')
}

export async function listAuditRecent(params: { limit?: number; role?: string; task_id?: string } = {}) {
  return request.get('/ai/skills/audit/recent', { params })
}

export async function clearAudit() {
  return request.delete('/ai/skills/audit')
}

export async function discoverFor(text: string) {
  return request.post('/ai/skills/discover', { text })
}

export async function listAuditPersisted(params: { limit?: number; offset?: number; role?: string; task_id?: string; skill_id?: string } = {}) {
  return request.get('/ai/skills/audit/persisted', { params })
}

export async function getAuditStats() {
  return request.get('/ai/skills/audit/stats')
}

export async function getSkillsHealth() {
  return request.get('/ai/skills/health')
}
