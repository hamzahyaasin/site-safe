import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useAuth } from '../context/AuthContext.jsx'
import { useWebSocket } from '../hooks/useWebSocket.js'

const SIM_ICONS = {
  ppe: '⛑️',
  sos: '🆘',
  zone_breach: '🚧',
  inactivity: '💤',
}

function formatTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
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

function demoLocation() {
  return {
    lat: 33.6844 + (Math.random() - 0.5) * 0.01,
    lng: 73.0479 + (Math.random() - 0.5) * 0.01,
  }
}

/** Backend returns `alerts_by_type` as an object { TYPE: count } or legacy array. */
function alertsByTypeToChartData(alertsByType) {
  if (!alertsByType) return []
  if (Array.isArray(alertsByType)) {
    return alertsByType.map((row) => ({
      name: row.name ?? row.type,
      count: Number(row.count ?? 0),
      label: String(row.name ?? row.type ?? '').replace(/_/g, ' '),
    }))
  }
  return Object.entries(alertsByType).map(([name, count]) => ({
    name,
    count: Number(count),
    label: name.replace(/_/g, ' '),
  }))
}

export default function DashboardPage() {
  const { api } = useAuth()
  const [stats, setStats] = useState(null)
  const [liveAlerts, setLiveAlerts] = useState([])
  const [highlightIds, setHighlightIds] = useState(() => new Set())
  const [workers, setWorkers] = useState([])
  const [workerId, setWorkerId] = useState('')
  const [toast, setToast] = useState('')
  const [loadingSim, setLoadingSim] = useState(null)
  const loadStatsRef = useRef(null)

  const loadStats = useCallback(async () => {
    const { data } = await api.get('dashboard/stats/')
    setStats(data)
  }, [api])
  loadStatsRef.current = loadStats

  const loadLiveAlerts = useCallback(async () => {
    const { data } = await api.get('alerts/', { params: { is_resolved: 'false' } })
    const list = Array.isArray(data) ? data : data.results || []
    setLiveAlerts(list.slice(0, 20))
  }, [api])

  const handleNewAlert = useCallback((payload) => {
    setLiveAlerts((prev) => {
      if (prev.some((a) => a.id === payload.id)) {
        return prev
      }
      return [
        {
          id: payload.id,
          alert_type: payload.alert_type,
          severity: payload.severity,
          description: payload.description,
          worker_name: payload.worker_name,
          timestamp: payload.timestamp,
          is_resolved: false,
        },
        ...prev,
      ].slice(0, 20)
    })
    setHighlightIds((prev) => new Set(prev).add(payload.id))
    window.setTimeout(() => {
      setHighlightIds((prev) => {
        const next = new Set(prev)
        next.delete(payload.id)
        return next
      })
    }, 2500)
    loadStatsRef.current?.()
  }, [])

  useWebSocket(handleNewAlert)

  const loadWorkers = useCallback(async () => {
    const { data } = await api.get('workers/')
    setWorkers(Array.isArray(data) ? data : data.results || [])
  }, [api])

  useEffect(() => {
    loadStats()
    loadWorkers()
    loadLiveAlerts()
  }, [loadStats, loadWorkers, loadLiveAlerts])

  useEffect(() => {
    if (workers.length && !workerId) {
      setWorkerId(String(workers[0].id))
    }
  }, [workers, workerId])

  function showToast(msg) {
    setToast(msg)
    window.setTimeout(() => setToast(''), 3500)
  }

  async function simulate(kind) {
    if (!workerId) {
      showToast('Select a worker first')
      return
    }
    const payloads = {
      ppe: {
        alert_type: 'PPE_VIOLATION',
        severity: 'HIGH',
        source: 'SIMULATED',
        worker_id: Number(workerId),
        location: demoLocation(),
      },
      sos: {
        alert_type: 'SOS',
        severity: 'CRITICAL',
        source: 'SIMULATED',
        worker_id: Number(workerId),
        location: demoLocation(),
      },
      zone_breach: {
        alert_type: 'ZONE_BREACH',
        severity: 'HIGH',
        source: 'SIMULATED',
        worker_id: Number(workerId),
        location: demoLocation(),
      },
      inactivity: {
        alert_type: 'INACTIVITY',
        severity: 'MEDIUM',
        source: 'SIMULATED',
        worker_id: Number(workerId),
        location: demoLocation(),
      },
    }
    setLoadingSim(kind)
    try {
      await api.post('alerts/simulate/', payloads[kind])
      showToast('Alert sent successfully')
    } catch (e) {
      showToast(e.response?.data?.detail || 'Failed to send alert')
    } finally {
      setLoadingSim(null)
    }
  }

  const chartData = alertsByTypeToChartData(stats?.alerts_by_type)

  return (
    <div className="page dashboard">
      <h1 className="page__title">Dashboard</h1>
      <p className="page__lead">Live overview of workers and safety alerts</p>

      <section className="stat-grid">
        <article className="stat-card">
          <span className="stat-card__label">Total Workers</span>
          <span className="stat-card__value">{stats?.total_workers ?? '—'}</span>
        </article>
        <article className="stat-card">
          <span className="stat-card__label">Active Workers</span>
          <span className="stat-card__value">{stats?.active_workers ?? '—'}</span>
        </article>
        <article className="stat-card">
          <span className="stat-card__label">Active Alerts</span>
          <span className="stat-card__value stat-card__value--warn">{stats?.unresolved_alerts ?? '—'}</span>
        </article>
        <article className="stat-card">
          <span className="stat-card__label">Critical Alerts</span>
          <span className="stat-card__value stat-card__value--danger">{stats?.critical_alerts ?? '—'}</span>
        </article>
        <article className="stat-card">
          <span className="stat-card__label">Alerts Today</span>
          <span className="stat-card__value">{stats?.total_alerts_today ?? '—'}</span>
        </article>
      </section>

      <section className="panel chart-panel">
        <h2 className="panel__title">Alerts by Type</h2>
        <p className="panel__muted">Unresolved alert counts by category</p>
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartData} margin={{ top: 16, right: 16, left: 0, bottom: 64 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3344" />
              <XAxis
                dataKey="label"
                stroke="#8b98a8"
                interval={0}
                angle={-35}
                textAnchor="end"
                height={70}
                tick={{ fontSize: 11 }}
              />
              <YAxis stroke="#8b98a8" allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #2a3344', borderRadius: 8 }}
                labelStyle={{ color: '#e5e7eb' }}
              />
              <Bar dataKey="count" fill="#38bdf8" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="panel">
        <h2 className="panel__title">
          Live Alert Feed
          <span className="count-badge">{liveAlerts.length}</span>
        </h2>
        <p className="panel__muted">Updates in real time via WebSocket</p>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Worker</th>
                <th>Type</th>
                <th>Severity</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {liveAlerts.length === 0 ? (
                <tr>
                  <td colSpan={5} className="empty-cell">
                    No active alerts.
                  </td>
                </tr>
              ) : (
                liveAlerts.map((a) => (
                  <tr
                    key={a.id}
                    className={
                      highlightIds.has(a.id)
                        ? 'data-table__row data-table__row--new'
                        : 'data-table__row'
                    }
                  >
                    <td>{formatTime(a.timestamp)}</td>
                    <td>{a.worker_name || '—'}</td>
                    <td>{a.alert_type?.replace(/_/g, ' ')}</td>
                    <td>
                      <span className={severityClass(a.severity)}>{a.severity}</span>
                    </td>
                    <td>{a.description || '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="sim-panel">
        <h2 className="sim-panel__title">IoT Vest Simulator (Hardware Not Connected)</h2>
        <p className="sim-panel__subtitle">Use these buttons to simulate IoT Smart Vest events</p>

        <div className="sim-panel__row">
          <label className="field field--inline">
            <span className="field__label">Worker</span>
            <select
              className="field__select"
              value={workerId}
              onChange={(e) => setWorkerId(e.target.value)}
              disabled={workers.length === 0}
            >
              {workers.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name} ({w.vest_id})
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="sim-buttons">
          <button
            type="button"
            className="sim-btn"
            disabled={!!loadingSim || workers.length === 0}
            onClick={() => simulate('ppe')}
          >
            <span className="sim-btn__icon" aria-hidden>
              {SIM_ICONS.ppe}
            </span>
            <span className="sim-btn__label">PPE Violation</span>
          </button>
          <button
            type="button"
            className="sim-btn"
            disabled={!!loadingSim || workers.length === 0}
            onClick={() => simulate('sos')}
          >
            <span className="sim-btn__icon" aria-hidden>
              {SIM_ICONS.sos}
            </span>
            <span className="sim-btn__label">SOS Alert</span>
          </button>
          <button
            type="button"
            className="sim-btn"
            disabled={!!loadingSim || workers.length === 0}
            onClick={() => simulate('zone_breach')}
          >
            <span className="sim-btn__icon" aria-hidden>
              {SIM_ICONS.zone_breach}
            </span>
            <span className="sim-btn__label">Zone Breach</span>
          </button>
          <button
            type="button"
            className="sim-btn"
            disabled={!!loadingSim || workers.length === 0}
            onClick={() => simulate('inactivity')}
          >
            <span className="sim-btn__icon" aria-hidden>
              {SIM_ICONS.inactivity}
            </span>
            <span className="sim-btn__label">Inactivity</span>
          </button>
        </div>
      </section>

      {toast ? (
        <div className="toast toast--success" role="status">
          {toast}
        </div>
      ) : null}
    </div>
  )
}
