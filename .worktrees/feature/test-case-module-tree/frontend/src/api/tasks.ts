import request from '../utils/request'

export async function listTasks(params: Record<string, any>) {
  return request.get('/tasks', { params })
}

export async function retryTask(taskId: string) {
  return request.post(`/tasks/${taskId}/retries`)
}

export async function deleteTaskById(taskId: string) {
  return request.delete(`/tasks/${taskId}`)
}

export async function batchDeleteTasks(taskIds: string[]) {
  return request.delete('/tasks', { data: { task_ids: taskIds } })
}

export async function getTaskDetail(taskId: string) {
  return request.get(`/tasks/${taskId}`)
}

export function buildTaskEventsUrl(taskId: string) {
  return `/api/tasks/${taskId}/events`
}

export async function getTaskMindMapData(taskId: string) {
  return request.get(`/tasks/${taskId}/mindmap-data`)
}

export async function updateReviewCases(taskId: string, payload: any) {
  return request.put(`/tasks/${taskId}/review-cases`, payload)
}

export async function exportCasesExcel(cases: any[]) {
  return request.post('/tasks/exports/excel', { cases }, { responseType: 'blob' })
}

export async function exportCasesXmind(cases: any[], title: string) {
  return request.post('/tasks/exports/xmind', { cases, title }, { responseType: 'blob' })
}

export async function syncCasesToMs(cases: any[]) {
  return request.post('/tasks/sync/ms', { cases })
}
