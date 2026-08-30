export function formatRelativeTime(isoString) {
  if (!isoString) return '—'
  const then = new Date(isoString)
  const now = new Date()
  const diffMs = now - then
  const diffMin = Math.floor(diffMs / 60000)

  if (diffMin < 1) return 'Just now'
  if (diffMin === 1) return '1 minute ago'
  if (diffMin < 60) return `${diffMin} minutes ago`

  const diffHr = Math.floor(diffMin / 60)
  if (diffHr === 1) return '1 hour ago'
  return `${diffHr} hours ago`
}

export function statusLabel(status) {
  const map = {
    Low: 'Quiet',
    Moderate: 'Moderately Busy',
    High: 'Busy',
    Closed: 'Closed',
  }
  return map[status] || status
}

export function statusColor(status) {
  const map = {
    Low: 'var(--color-low)',
    Moderate: 'var(--color-medium)',
    High: 'var(--color-high)',
    Closed: 'var(--color-muted)',
  }
  return map[status] || 'var(--color-muted)'
}

export function formatTime12h(time24) {
  if (!time24) return '—'
  const [h] = time24.split(':').map(Number)
  const period = h >= 12 ? 'PM' : 'AM'
  const hr12 = h % 12 || 12
  return `${String(hr12).padStart(2, '0')}:00 ${period}`
}
