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

export function cameraIdFromSource(source) {
  switch (source) {
    case 'AI_CAMERA':
      return 'CAM-01'
    case 'SMART_VEST':
      return 'VEST-LINK'
    case 'SIMULATED':
      return 'SIM'
    default:
      return '—'
  }
}

/** Prefer the alert's real camera_id (set by ai-module for a named camera
 * source) and only fall back to the generic source-derived placeholder
 * when one isn't attached. */
export function displayCameraId(alert) {
  return alert?.camera_id || cameraIdFromSource(alert?.source)
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

/** Demo-friendly last-seen: active workers appear recently online for FYP demos. */
export function deriveLastSeen(worker) {
  if (!worker.is_active) {
    const daysAgo = 2 + (worker.id % 5)
    return new Date(Date.now() - daysAgo * 86400000).toISOString()
  }
  const minutesAgo = 1 + ((worker.id * 3) % 4)
  return new Date(Date.now() - minutesAgo * 60000).toISOString()
}

export function getWorkerPresenceStatus(worker, lastSeenIso) {
  if (!worker.is_active) {
    return { label: 'OFFLINE', variant: 'offline' }
  }
  const diffMs = Date.now() - new Date(lastSeenIso).getTime()
  const mins = diffMs / 60000
  if (mins <= 5) return { label: 'ACTIVE', variant: 'active' }
  if (mins <= 60) return { label: 'WARNING', variant: 'atRisk' }
  return { label: 'OFFLINE', variant: 'offline' }
}

/** Deterministic pseudo-vitals from worker id (UI placeholder until IoT API exists). */
export function deriveWorkerVitals(worker) {
  const seed = worker.id * 17 + (worker.vest_id?.length || 0) * 3
  return {
    temp: (36.2 + (seed % 15) / 10).toFixed(1),
    heartRate: 68 + (seed % 28),
    gasPpm: seed % 12,
  }
}

export function deriveComplianceRate(stats) {
  if (!stats) return null
  const active = stats.active_workers || 0
  const open = stats.unresolved_alerts || 0
  if (active === 0) return 100
  return Math.max(0, Math.min(100, Math.round(((active - open) / active) * 100)))
}

export function sparklineFromValue(value, points = 8) {
  const base = Number(value) || 0
  return Array.from({ length: points }, (_, i) => ({
    v: Math.max(0, base + Math.sin(i * 1.2 + base) * (base * 0.08 + 1)),
  }))
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
