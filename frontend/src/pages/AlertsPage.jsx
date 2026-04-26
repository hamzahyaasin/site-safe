import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'unresolved', label: 'Unresolved' },
  { id: 'critical', label: 'Critical' },
]

function formatTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

function sourceLabel(source) {
  switch (source) {
    case 'AI_CAMERA':
      return 'AI Camera'
    case 'IOT_VEST':
      return 'IoT Vest'
    case 'SIMULATED':
      return 'Simulated'
    default:
      return source || '—'
  }
}

function severityClass(sev) {
  switch (sev) {
    case 'CRITICAL':
      return 'badge badge--critical'
    case 'HIGH':
      return 'badge badge--high'
    case 'MEDIUM':
      return 'badge badge--medium'
    case 'LOW':
      return 'badge badge--low'
    default:
      return 'badge'
  }
}

function sourceClass(src) {
  switch (src) {
    case 'AI_CAMERA':
      return 'badge badge--src-ai'
    case 'IOT_VEST':
      return 'badge badge--src-iot'
    case 'SIMULATED':
      return 'badge badge--src-sim'
    default:
      return 'badge'
  }
}

export default function AlertsPage() {
  const { api } = useAuth()
  const [filter, setFilter] = useState('unresolved')
  const [alerts, setAlerts] = useState([])
  const [highlightIds, setHighlightIds] = useState(() => new Set())
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
      if (!prev.has(id)) {
        fresh.add(id)
      }
    }
    prevIdsRef.current = nextIds
    if (prev.size > 0 && fresh.size > 0) {
      setHighlightIds(fresh)
      window.setTimeout(() => setHighlightIds(new Set()), 2500)
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
    await api.post(`alerts/${id}/resolve/`)
    await fetchAlerts()
  }

  return (
    <div className="page alerts-page">
      <header className="page-header">
        <div>
          <h1 className="page__title">
            Live Alerts
            <span className="count-badge">{alerts.length}</span>
          </h1>
          <p className="page__lead">Auto-refresh every 5 seconds</p>
        </div>
        <div className="filter-bar">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              className={filter === f.id ? 'chip chip--active' : 'chip'}
              onClick={() => setFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </header>

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
                  No alerts for this filter.
                </td>
              </tr>
            ) : (
              alerts.map((a) => (
                <tr
                  key={a.id}
                  className={highlightIds.has(a.id) ? 'data-table__row data-table__row--new' : 'data-table__row'}
                >
                  <td>{formatTime(a.timestamp)}</td>
                  <td>{a.worker_name}</td>
                  <td>
                    <code>{a.vest_id}</code>
                  </td>
                  <td>{a.alert_type?.replace(/_/g, ' ')}</td>
                  <td>
                    <span className={severityClass(a.severity)}>{a.severity}</span>
                  </td>
                  <td>
                    <span className={sourceClass(a.source)}>{sourceLabel(a.source)}</span>
                  </td>
                  <td>{a.is_resolved ? <span className="badge badge--low">Resolved</span> : <span className="badge badge--high">Open</span>}</td>
                  <td>
                    {!a.is_resolved ? (
                      <button type="button" className="btn btn--sm btn--ghost" onClick={() => resolveAlert(a.id)}>
                        Resolve
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
