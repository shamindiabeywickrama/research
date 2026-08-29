const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function handle(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${res.status})`)
  }
  return res.json()
}

export async function getRoot() {
  const res = await fetch(`${API_BASE}/`)
  return handle(res)
}

export async function predictHour(date, hour) {
  const res = await fetch(`${API_BASE}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ date, hour }),
  })
  return handle(res)
}

export async function predictDay(date) {
  const res = await fetch(`${API_BASE}/predict/day?date_str=${date}`)
  return handle(res)
}

export async function getHistory(limit = 20) {
  const res = await fetch(`${API_BASE}/history?limit=${limit}`)
  return handle(res)
}
