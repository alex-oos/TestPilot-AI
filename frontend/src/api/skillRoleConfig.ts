import request from '../utils/request'

export interface SkillRoleBindingItem {
  role: string
  config_id: string
  skill_id: string
  enabled: boolean
  effective_skill_id: string
  source: string
  skill_exists: boolean
  default_skill_id: string
  env_override: string
}

export interface SkillRoleBindingResponse {
  qa_skills_enabled: boolean
  env_qa_skills_enabled: boolean
  roles: SkillRoleBindingItem[]
}

export interface SkillRoleBindingUpdatePayload {
  qa_skills_enabled?: boolean
  skill_configs?: Array<{
    id?: string
    role: string
    skill_id: string
    enabled: boolean
  }>
}

/** 读取 QA Skill 三角色绑定与全局开关 */
export async function getSkillRoleBinding() {
  return request.get<SkillRoleBindingResponse>('/ai/skill-role-config')
}

/** 更新 QA Skill 三角色绑定与全局开关 */
export async function updateSkillRoleBinding(payload: SkillRoleBindingUpdatePayload) {
  return request.put<SkillRoleBindingResponse>('/ai/skill-role-config', payload)
}
