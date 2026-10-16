export function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

export function initials(name) {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0][0].toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

export function formatAlertType(type) {
  return type ? String(type).replace(/_/g, ' ') : '—'
}

export function sourceLabel(source) {
  switch (source) {
    case 'AI_CAMERA':
      return 'AI Camera'
    case 'SMART_VEST':
      return 'Smart Vest'
    case 'SIMULATED':
      return 'Simulated'
    default:
      return source || '—'
  }
}

/** The camera that raised an alert, if any. Vest and simulated alerts have none. */
export function displayCameraId(alert) {
  return alert?.camera_id || '—'
}

/** e.g. "2 min ago · 14:32 PKT" */
export function formatTimestamp(iso) {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'

  const diff = Date.now() - date.getTime()
  const mins = Math.floor(diff / 60000)
  let relative = 'just now'
  if (mins >= 1 && mins < 60) relative = `${mins} min ago`
  else if (mins >= 60 && mins < 1440) relative = `${Math.floor(mins / 60)} hr ago`
  else if (mins >= 1440) relative = `${Math.floor(mins / 1440)} d ago`

  const absolute = date.toLocaleString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  })

  return `${relative} · ${absolute}`
}

export function formatDateTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export function severityStripeClass(severity) {
  switch (severity) {
    case 'CRITICAL':
      return 'border-l-red-500'
    case 'HIGH':
      return 'border-l-amber-500'
    case 'MEDIUM':
      return 'border-l-yellow-500'
    case 'LOW':
      return 'border-l-blue-500'
    default:
      return 'border-l-zinc-600'
  }
}

export function severityBadgeVariant(severity) {
  switch (severity) {
    case 'CRITICAL':
      return 'critical'
    case 'HIGH':
      return 'high'
    case 'MEDIUM':
      return 'medium'
    case 'LOW':
      return 'low'
    default:
      return 'neutral'
  }
}

export function normalizeList(data) {
  return Array.isArray(data) ? data : data?.results || []
}

/** Presence from the worker's vest telemetry; there is no presence signal
 * for a worker without a vest, so that is reported as untracked rather
 * than guessed. */
export function getWorkerPresence(worker) {
  if (!worker.is_active) return { label: 'INACTIVE', variant: 'offline', lastSeen: null }
  const vest = worker.smart_vest
  if (!vest) return { label: 'NO VEST', variant: 'neutral', lastSeen: null }
  if (!vest.last_seen) return { label: 'NEVER REPORTED', variant: 'offline', lastSeen: null }
  if (vest.sos_active) return { label: 'SOS', variant: 'critical', lastSeen: vest.last_seen }
  if (vest.is_online) return { label: 'ON SITE', variant: 'active', lastSeen: vest.last_seen }
  return { label: 'OFFLINE', variant: 'offline', lastSeen: vest.last_seen }
}

/** Short local label for an ISO date, e.g. "Thu 16". */
export function shortDayLabel(isoDate) {
  const [y, m, d] = isoDate.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' })
}

export function formatMinutes(mins) {
  if (mins === null || mins === undefined) return null
  if (mins < 60) return `${Math.round(mins)} min`
  const h = Math.floor(mins / 60)
  const m = Math.round(mins % 60)
  return m ? `${h} h ${m} min` : `${h} h`
}

export function browserTimeZone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone
  } catch {
    return undefined
  }
}

export function exportCsv(filename, headers, rows) {
  const escape = (cell) => {
    const s = String(cell ?? '')
    if (s.includes(',') || s.includes('"') || s.includes('\n')) {
      return `"${s.replace(/"/g, '""')}"`
    }
    return s
  }
  const lines = [headers.join(','), ...rows.map((r) => r.map(escape).join(','))]
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
