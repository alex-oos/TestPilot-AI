export function formatNow() {
  const now = new Date()
  const y = now.getFullYear()
  const m = `${now.getMonth() + 1}`.padStart(2, '0')
  const d = `${now.getDate()}`.padStart(2, '0')
  const hh = `${now.getHours()}`.padStart(2, '0')
  const mm = `${now.getMinutes()}`.padStart(2, '0')
  return `${y}/${m}/${d} ${hh}:${mm}`
}

export function newId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}
