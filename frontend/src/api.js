const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function handle(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${res.status})`)
  }
  return res.json()
}

export async function getHealth() {
  const res = await fetch(`${API_BASE}/api/health`)
  return handle(res)
}

export async function getCurrentOccupancy() {
  const res = await fetch(`${API_BASE}/api/library/current`)
  return handle(res)
}

export async function getForecast() {
  const res = await fetch(`${API_BASE}/api/library/forecast`)
  return handle(res)
}

export async function getRecommendations() {
  const res = await fetch(`${API_BASE}/api/library/recommendations`)
  return handle(res)
}

export async function getMetrics() {
  const res = await fetch(`${API_BASE}/api/library/metrics`)
  return handle(res)
}

export async function getDataSources() {
  const res = await fetch(`${API_BASE}/api/library/data-sources`)
  return handle(res)
}

export async function getNetworkStatus() {
  const res = await fetch(`${API_BASE}/api/network/status`)
  return handle(res)
}

export async function getNetworkEvents() {
  const res = await fetch(`${API_BASE}/api/network/events`)
  return handle(res)
}

export function connectNetworkWebSocket(onMessage, onError) {
  const wsUrl = API_BASE.replace(/^http/, 'ws') + '/ws/network'
  const ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('WebSocket connected')
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch (e) {
      console.error('WebSocket parse error:', e)
    }
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
    if (onError) onError(error)
  }

  ws.onclose = () => {
    console.log('WebSocket disconnected')
  }

  return ws
}

export { API_BASE }
