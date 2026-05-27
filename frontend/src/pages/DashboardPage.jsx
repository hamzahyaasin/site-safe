import { useCallback, useEffect, useState } from 'react'
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

function IconUsers() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  )
}

function IconActivity() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  )
}

function IconBell() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  )
}

function IconAlert() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="10.29 3.86 1.82 18 22.18 18 13.71 3.86 10.29 3.86" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  )
}

function IconCalendar() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  )
}

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

function dotClass(severity) {
  switch (severity) {
    case 'CRITICAL': return 'recent-item__dot recent-item__dot--critical'
    case 'HIGH': return 'recent-item__dot recent-item__dot--high'
    case 'MEDIUM': return 'recent-item__dot recent-item__dot--medium'
    default: return 'recent-item__dot recent-item__dot--low'
  }
}

function relativeTime(iso) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: '#0f1e30', border: '1px solid #1b2d42', borderRadius: 8, padding: '0.55rem 0.75rem' }}>
      <p style={{ margin: '0 0 0.2rem', color: '#9db3c8', fontSize: '0.75rem', textTransform: 'capitalize' }}>{label}</p>
      <p style={{ margin: 0, color: '#38bdf8', fontWeight: 700 }}>{payload[0].value} alert{payload[0].value !== 1 ? 's' : ''}</p>
    </div>
  )
}

export default function DashboardPage() {
  const { api } = useAuth()
  const [stats, setStats] = useState(null)
  const [workers, setWorkers] = useState([])
  const [recentAlerts, setRecentAlerts] = useState([])
  const [workerId, setWorkerId] = useState('')
  const [toast, setToast] = useState({ msg: '', type: 'success' })
  const [loadingSim, setLoadingSim] = useState(null)

  const loadStats = useCallback(async () => {
    const { data } = await api.get('dashboard/stats/')
    setStats(data)
  }, [api])

  const loadWorkers = useCallback(async () => {
    const { data } = await api.get('workers/')
    setWorkers(Array.isArray(data) ? data : data.results || [])
  }, [api])

  const loadRecent = useCallback(async () => {
    const { data } = await api.get('alerts/', { params: { is_resolved: 'false', ordering: '-timestamp' } })
    const list = Array.isArray(data) ? data : data.results || []
    setRecentAlerts(list.slice(0, 6))
  }, [api])

  useEffect(() => {
    loadStats()
    loadWorkers()
    loadRecent()
  }, [loadStats, loadWorkers, loadRecent])

  useEffect(() => {
    if (workers.length && !workerId) setWorkerId(String(workers[0].id))
  }, [workers, workerId])

  function showToast(msg, type = 'success') {
    setToast({ msg, type })
    window.setTimeout(() => setToast({ msg: '', type: 'success' }), 3500)
  }

  async function simulate(kind) {
    if (!workerId) { showToast('Select a worker first', 'error'); return }
    const payloads = {
      fall: { alert_type: 'FALL', severity: 'CRITICAL', source: 'SIMULATED', worker_id: Number(workerId) },
      gas: { alert_type: 'GAS_LEAK', severity: 'HIGH', source: 'SIMULATED', worker_id: Number(workerId) },
      heat: { alert_type: 'HEAT_STRESS', severity: 'MEDIUM', source: 'SIMULATED', worker_id: Number(workerId) },
      sos: { alert_type: 'SOS', severity: 'CRITICAL', source: 'SIMULATED', worker_id: Number(workerId) },
    }
    setLoadingSim(kind)
    try {
      await api.post('alerts/simulate/', payloads[kind])
      showToast('Alert simulated successfully')
      await Promise.all([loadStats(), loadRecent()])
    } catch (e) {
      showToast(e.response?.data?.detail || 'Failed to send alert', 'error')
    } finally {
      setLoadingSim(null)
    }
  }

  const chartData = alertsByTypeToChartData(stats?.alerts_by_type)

  return (
    <div className="page dashboard">
      <div className="page__header">
        <p className="page__eyebrow">Overview</p>
        <h1 className="page__title">Safety Dashboard</h1>
        <p className="page__lead">Live site status — workers, PPE compliance, and active incidents</p>
      </div>

      {/* KPI stat grid */}
      <section className="stat-grid">
        <article className="stat-card">
          <div className="stat-card__top">
            <span className="stat-card__label">Total Workers</span>
            <div className="stat-card__icon stat-card__icon--blue"><IconUsers /></div>
          </div>
          <span className="stat-card__value">{stats?.total_workers ?? '—'}</span>
        </article>

        <article className="stat-card">
          <div className="stat-card__top">
            <span className="stat-card__label">Active Workers</span>
            <div className="stat-card__icon stat-card__icon--green"><IconActivity /></div>
          </div>
          <span className="stat-card__value stat-card__value--success">{stats?.active_workers ?? '—'}</span>
        </article>

        <article className="stat-card">
          <div className="stat-card__top">
            <span className="stat-card__label">Open Alerts</span>
            <div className="stat-card__icon stat-card__icon--orange"><IconBell /></div>
          </div>
          <span className="stat-card__value stat-card__value--warn">{stats?.unresolved_alerts ?? '—'}</span>
        </article>

        <article className="stat-card">
          <div className="stat-card__top">
            <span className="stat-card__label">Critical Alerts</span>
            <div className="stat-card__icon stat-card__icon--red"><IconAlert /></div>
          </div>
          <span className="stat-card__value stat-card__value--danger">{stats?.critical_alerts ?? '—'}</span>
        </article>

        <article className="stat-card">
          <div className="stat-card__top">
            <span className="stat-card__label">Alerts Today</span>
            <div className="stat-card__icon stat-card__icon--purple"><IconCalendar /></div>
          </div>
          <span className="stat-card__value">{stats?.total_alerts_today ?? '—'}</span>
        </article>
      </section>

      {/* Chart + Recent alerts */}
      <div className="dashboard-grid">
        <div className="panel" style={{ marginBottom: 0 }}>
          <div className="panel__header">
            <div className="panel__heading">
              <h2 className="panel__title">Alerts by Type</h2>
              <p className="panel__subtitle">Unresolved alert distribution across categories</p>
            </div>
          </div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData} margin={{ top: 8, right: 12, left: -8, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1b2d42" vertical={false} />
                <XAxis
                  dataKey="label"
                  stroke="#627a92"
                  interval={0}
                  angle={-35}
                  textAnchor="end"
                  height={68}
                  tick={{ fontSize: 11, fill: '#627a92' }}
                  axisLine={{ stroke: '#1b2d42' }}
                  tickLine={false}
                />
                <YAxis
                  stroke="#627a92"
                  allowDecimals={false}
                  tick={{ fontSize: 11, fill: '#627a92' }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(56, 189, 248, 0.06)' }} />
                <Bar dataKey="count" fill="#38bdf8" radius={[6, 6, 0, 0]} maxBarSize={48} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="panel" style={{ marginBottom: 0 }}>
          <div className="panel__header">
            <div className="panel__heading">
              <h2 className="panel__title">Recent Incidents</h2>
              <p className="panel__subtitle">Latest unresolved alerts</p>
            </div>
          </div>
          {recentAlerts.length === 0 ? (
            <div className="recent-empty">
              <div className="recent-empty__icon">✅</div>
              <p>No open incidents</p>
            </div>
          ) : (
            <div className="recent-list">
              {recentAlerts.map((a) => (
                <div key={a.id} className="recent-item">
                  <div className={dotClass(a.severity)} />
                  <span className="recent-item__type">{a.alert_type?.replace(/_/g, ' ')}</span>
                  <span className="recent-item__worker">{a.worker_name}</span>
                  <span className="recent-item__time">{relativeTime(a.timestamp)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* IoT Simulator */}
      <section className="sim-panel">
        <div className="sim-panel__header">
          <div className="sim-panel__text">
            <h2 className="sim-panel__title">IoT Vest Simulator</h2>
            <p className="sim-panel__subtitle">Simulate smart vest events for testing and demonstration</p>
          </div>
          <span className="sim-panel__tag">Hardware Offline</span>
        </div>

        <div className="sim-worker-row">
          <label className="field" style={{ maxWidth: 320 }}>
            <span className="field__label">Target Worker</span>
            <select
              className="field__select"
              value={workerId}
              onChange={(e) => setWorkerId(e.target.value)}
              disabled={workers.length === 0}
            >
              {workers.length === 0 ? (
                <option>No workers found</option>
              ) : (
                workers.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} — {w.vest_id}
                  </option>
                ))
              )}
            </select>
          </label>
        </div>

        <div className="sim-buttons">
          <button
            type="button"
            className="sim-btn sim-btn--fall"
            disabled={!!loadingSim || workers.length === 0}
            onClick={() => simulate('fall')}
          >
            <span className="sim-btn__icon">🔴</span>
            <span>
              <span className="sim-btn__label">Fall Detected</span>
              <span className="sim-btn__meta">CRITICAL severity</span>
            </span>
          </button>

          <button
            type="button"
            className="sim-btn sim-btn--gas"
            disabled={!!loadingSim || workers.length === 0}
            onClick={() => simulate('gas')}
          >
            <span className="sim-btn__icon">💨</span>
            <span>
              <span className="sim-btn__label">Gas Leak</span>
              <span className="sim-btn__meta">HIGH severity</span>
            </span>
          </button>

          <button
            type="button"
            className="sim-btn sim-btn--heat"
            disabled={!!loadingSim || workers.length === 0}
            onClick={() => simulate('heat')}
          >
            <span className="sim-btn__icon">🌡️</span>
            <span>
              <span className="sim-btn__label">Heat Stress</span>
              <span className="sim-btn__meta">MEDIUM severity</span>
            </span>
          </button>

          <button
            type="button"
            className="sim-btn sim-btn--sos"
            disabled={!!loadingSim || workers.length === 0}
            onClick={() => simulate('sos')}
          >
            <span className="sim-btn__icon">🆘</span>
            <span>
              <span className="sim-btn__label">SOS Pressed</span>
              <span className="sim-btn__meta">CRITICAL severity</span>
            </span>
          </button>
        </div>
      </section>

      {toast.msg ? (
        <div className={`toast toast--${toast.type}`} role="status">
          {toast.type === 'success' ? '✓' : '⚠'} {toast.msg}
        </div>
      ) : null}
    </div>
  )
}
