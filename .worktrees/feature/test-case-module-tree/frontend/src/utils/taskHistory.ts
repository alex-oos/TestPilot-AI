export interface TaskHistoryItem {
  id: string
  sourceType: string
  sourceLabel: string
  status: string
  createdAt: string
  updatedAt: string
}

const TASK_HISTORY_KEY = 'task_history'

function parseHistory(raw: string | null): TaskHistoryItem[] {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((item) => item && typeof item.id === 'string')
  } catch {
    return []
  }
}

export function getTaskHistory(): TaskHistoryItem[] {
  const tasks = parseHistory(localStorage.getItem(TASK_HISTORY_KEY))
  return tasks.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
}

export function addTaskToHistory(params: {
  id: string
  sourceType: string
  sourceLabel: string
}) {
  const now = new Date().toISOString()
  const tasks = parseHistory(localStorage.getItem(TASK_HISTORY_KEY))
  const exists = tasks.find((t) => t.id === params.id)

  if (exists) {
    exists.sourceType = params.sourceType
    exists.sourceLabel = params.sourceLabel
    exists.updatedAt = now
    exists.status = exists.status || 'pending'
  } else {
    tasks.push({
      id: params.id,
      sourceType: params.sourceType,
      sourceLabel: params.sourceLabel,
      status: 'pending',
      createdAt: now,
      updatedAt: now,
    })
  }

  localStorage.setItem(TASK_HISTORY_KEY, JSON.stringify(tasks))
}

export function updateTaskStatusInHistory(taskId: string, status: string) {
  const tasks = parseHistory(localStorage.getItem(TASK_HISTORY_KEY))
  const target = tasks.find((t) => t.id === taskId)

  if (!target) return

  target.status = status
  target.updatedAt = new Date().toISOString()
  localStorage.setItem(TASK_HISTORY_KEY, JSON.stringify(tasks))
}
