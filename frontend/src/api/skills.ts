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
  protected?: boolean
  referenced_by_roles?: string[]
  deletable?: boolean
}

export interface SkillsListResponse {
  enabled: boolean
  env_enabled?: boolean
  fewshot_enabled: boolean
  discover_enabled: boolean
  ab_enabled: boolean
  legacy_fallback_enabled: boolean
  prompt_token_budget: number
  library_dir: string
  active_overlays: string[]
  skills: SkillSummary[]
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

export async function exportSkill(skillId: string) {
  return request.get(`/ai/skills/${encodeURIComponent(skillId)}/export`, {
    responseType: 'blob',
  })
}

export async function deleteSkill(skillId: string) {
  return request.delete(`/ai/skills/${encodeURIComponent(skillId)}`)
}

export interface GitHubSkillImportPayload {
  source: string
  branch?: string
  skill_id?: string
  overwrite?: boolean
}

export async function previewGithubSkillImport(payload: GitHubSkillImportPayload) {
  return request.post('/ai/skills/import/github/preview', payload)
}

export async function importGithubSkill(payload: GitHubSkillImportPayload) {
  return request.post('/ai/skills/import/github', payload)
}

export async function previewZipSkillImport(file: File, skillId?: string) {
  const form = new FormData()
  form.append('file', file)
  if (skillId?.trim()) {
    form.append('skill_id', skillId.trim())
  }
  return request.post('/ai/skills/import/zip/preview', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export async function importZipSkill(file: File, skillId?: string, overwrite = false) {
  const form = new FormData()
  form.append('file', file)
  if (skillId?.trim()) {
    form.append('skill_id', skillId.trim())
  }
  form.append('overwrite', overwrite ? 'true' : 'false')
  return request.post('/ai/skills/import/zip', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
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

// ---- 用例质量门禁 ----
export async function getTaskQuality(taskId: string) {
  return request.get(`/ai/quality/task/${encodeURIComponent(taskId)}`)
}

export async function scoreCases(cases: any[], lowThreshold?: number) {
  return request.post('/ai/quality/score', { cases, low_threshold: lowThreshold })
}

// ---- LLM 治理观测 ----
export async function getLlmCacheStats() {
  return request.get('/ai/llm/cache/stats')
}

export async function purgeLlmCache() {
  return request.post('/ai/llm/cache/purge')
}

export async function clearLlmCache() {
  return request.delete('/ai/llm/cache')
}

export async function getLlmConcurrencyStats() {
  return request.get('/ai/llm/concurrency/stats')
}

export async function getLlmPricing() {
  return request.get('/ai/llm/pricing')
}

export async function getLlmCostRecent(days = 7) {
  return request.get('/ai/llm/cost/recent', { params: { days } })
}

export async function getTaskLlmCalls(taskId: string) {
  return request.get(`/ai/llm/task/${encodeURIComponent(taskId)}/calls`)
}

export async function purgeAudit(days?: number) {
  return request.post('/ai/skills/audit/purge', null, { params: days ? { days } : undefined })
}
