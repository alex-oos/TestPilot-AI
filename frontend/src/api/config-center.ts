import request from '../utils/request'

export async function getAIModels() {
  return request.get('/config-center/ai-models/list')
}

export async function createAIModel(payload: any) {
  return request.post('/config-center/ai-models/create', payload)
}

export async function editAIModel(payload: any) {
  return request.put('/config-center/ai-models/edit', payload)
}

export async function deleteAIModel(configId: string) {
  return request.delete(`/config-center/ai-models/delete/${encodeURIComponent(configId)}`)
}

export async function testModelConnection(payload: any) {
  return request.post('/config-center/models/test', payload)
}

export async function getPrompts() {
  return request.get('/config-center/prompts/list')
}

export async function getPromptDefaults() {
  return request.get('/config-center/prompts/defaults')
}

export async function createPrompt(payload: any) {
  return request.post('/config-center/prompts/create', payload)
}

export async function editPrompt(payload: any) {
  return request.put('/config-center/prompts/edit', payload)
}

export async function deletePrompt(configId: string) {
  return request.delete(`/config-center/prompts/delete/${encodeURIComponent(configId)}`)
}

export async function getBehaviors() {
  return request.get('/config-center/behavior/list')
}

export async function createBehavior(payload: any) {
  return request.post('/config-center/behavior/create', payload)
}

export async function editBehavior(payload: any) {
  return request.put('/config-center/behavior/edit', payload)
}

export async function deleteBehavior(configId: string) {
  return request.delete(`/config-center/behavior/delete/${encodeURIComponent(configId)}`)
}

export async function getNotifications() {
  return request.get('/config-center/notifications/list')
}

export async function editNotification(channel: 'feishu' | 'wecom' | 'dingtalk', payload: any) {
  return request.put(`/config-center/notifications/edit/${channel}`, payload)
}
