import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'

const FILTERS = [
  { id: 'unresolved', label: 'Unresolved' },
  { id: 'critical', label: 'Critical' },
  { id: 'all', label: 'All' },
]

function formatTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function sourceLabel(source) {
  switch (source) {
    case 'AI_CAMERA': return 'AI Camera'
    case 'IOT_VEST': return 'IoT Vest'
    case 'SIMULATED': return 'Simulated'
    default: return source || '—'
  }
}

function severityClass(sev) {
  switch (sev) {
    case 'CRITICAL': return 'badge badge--critical'
    case 'HIGH': return 'badge badge--high'
    case 'MEDIUM': return 'badge badge--medium'
    case 'LOW': return 'badge badge--low'
    default: return 'badge'
  }
}

function sourceClass(src) {
  switch (src) {
    case 'AI_CAMERA': return 'badge badge--src-ai'
    case 'IOT_VEST': return 'badge badge--src-iot'
    case 'SIMULATED': return 'badge badge--src-sim'
    default: return 'badge'
  }
}

function rowClass(alert, isNew) {
  const base = isNew ? 'data-table__row--new' : ''
  if (alert.severity === 'CRITICAL') return `data-table__row--critical ${base}`.trim()
  if (alert.severity === 'HIGH') return `data-table__row--high ${base}`.trim()
  return base || undefined
}

export default function AlertsPage() {
  const { api } = useAuth()
  const [filter, setFilter] = useState('unresolved')
  const [alerts, setAlerts] = useState([])
  const [highlightIds, setHighlightIds] = useState(() => new Set())
  const [resolvingId, setResolvingId] = useState(null)
  const prevIdsRef = useRef(new Set())

  const query = useMemo(() => {
    if (filter === 'unresolved') return { is_resolved: 'false' }
    if (filter === 'critical') return { severity: 'CRITICAL', is_resolved: 'false' }
    return {}
  }, [filter])

  const fetchAlerts = useCallback(async () => {
    const { data } = await api.get('alerts/', { params: query })
    const list = Array.isArray(data) ? data : data.results || []
    const nextIds = new Set(list.map((a) => a.id))
    const prev = prevIdsRef.current
    const fresh = new Set()
    for (const id of nextIds) {
      if (!prev.has(id)) fresh.add(id)
    }
    prevIdsRef.current = nextIds
    if (prev.size > 0 && fresh.size > 0) {
      setHighlightIds(fresh)
      window.setTimeout(() => setHighlightIds(new Set()), 2600)
    }
    setAlerts(list)
  }, [api, query])

  useEffect(() => {
    prevIdsRef.current = new Set()
    fetchAlerts()
  }, [fetchAlerts, filter])

  useEffect(() => {
    const t = window.setInterval(fetchAlerts, 5000)
    return () => window.clearInterval(t)
  }, [fetchAlerts])

  async function resolveAlert(id) {
    setResolvingId(id)
    try {
      await api.post(`alerts/${id}/resolve/`)
      await fetchAlerts()
    } finally {
      setResolvingId(null)
    }
  }

  return (
    <div className="page alerts-page">
      <div className="page__header">
        <p className="page__eyebrow">Monitoring</p>
        <h1 className="page__title">
          Live Alerts
          <span className="count-badge">{alerts.length}</span>
        </h1>
        <p className="page__lead">Safety incidents from AI camera, IoT vests, and simulated sources</p>
      </div>

      <div className="page__header-row" style={{ marginBottom: '1.25rem' }}>
        <div className="filter-bar">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              className={filter === f.id ? 'filter-chip filter-chip--active' : 'filter-chip'}
              onClick={() => setFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <span className="live-indicator">
          <span className="live-dot" />
          Auto-refresh every 5s
        </span>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Worker</th>
              <th>Vest ID</th>
              <th>Type</th>
              <th>Severity</th>
              <th>Source</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {alerts.length === 0 ? (
              <tr>
                <td colSpan={8} className="empty-cell">
                  <div style={{ fontSize: '1.8rem', marginBottom: '0.5rem', opacity: 0.4 }}>🔔</div>
                  No alerts match this filter
                </td>
              </tr>
            ) : (
              alerts.map((a) => (
                <tr key={a.id} className={rowClass(a, highlightIds.has(a.id))}>
                  <td className="muted" style={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>{formatTime(a.timestamp)}</td>
                  <td style={{ fontWeight: 500 }}>{a.worker_name || <span className="muted">—</span>}</td>
                  <td><code>{a.vest_id || '—'}</code></td>
                  <td style={{ whiteSpace: 'nowrap' }}>{a.alert_type?.replace(/_/g, ' ') || '—'}</td>
                  <td><span className={severityClass(a.severity)}>{a.severity}</span></td>
                  <td><span className={sourceClass(a.source)}>{sourceLabel(a.source)}</span></td>
                  <td>
                    {a.is_resolved
                      ? <span className="badge badge--low">✓ Resolved</span>
                      : <span className="badge badge--medium">● Open</span>}
                  </td>
                  <td>
                    {!a.is_resolved ? (
                      <button
                        type="button"
                        className="btn btn--sm btn--success"
                        disabled={resolvingId === a.id}
                        onClick={() => resolveAlert(a.id)}
                      >
                        {resolvingId === a.id ? '…' : 'Resolve'}
                      </button>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
