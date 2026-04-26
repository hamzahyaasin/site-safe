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

const SIM_ICONS = {
  fall: '🔴',
  gas: '🟡',
  heat: '🟠',
  sos: '🆘',
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
  const [workers, setWorkers] = useState([])
  const [workerId, setWorkerId] = useState('')
  const [toast, setToast] = useState('')
  const [loadingSim, setLoadingSim] = useState(null)

  const loadStats = useCallback(async () => {
    const { data } = await api.get('dashboard/stats/')
    setStats(data)
  }, [api])

  const loadWorkers = useCallback(async () => {
    const { data } = await api.get('workers/')
    setWorkers(Array.isArray(data) ? data : data.results || [])
  }, [api])

  useEffect(() => {
    loadStats()
    loadWorkers()
  }, [loadStats, loadWorkers])

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
      fall: { alert_type: 'FALL', severity: 'CRITICAL', source: 'SIMULATED', worker_id: Number(workerId) },
      gas: { alert_type: 'GAS_LEAK', severity: 'HIGH', source: 'SIMULATED', worker_id: Number(workerId) },
      heat: { alert_type: 'HEAT_STRESS', severity: 'MEDIUM', source: 'SIMULATED', worker_id: Number(workerId) },
      sos: { alert_type: 'SOS', severity: 'CRITICAL', source: 'SIMULATED', worker_id: Number(workerId) },
    }
    setLoadingSim(kind)
    try {
      await api.post('alerts/simulate/', payloads[kind])
      showToast('Alert sent successfully')
      await loadStats()
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
            onClick={() => simulate('fall')}
          >
            <span className="sim-btn__icon" aria-hidden>
              {SIM_ICONS.fall}
            </span>
            <span className="sim-btn__label">Fall Detected</span>
          </button>
          <button
            type="button"
            className="sim-btn"
            disabled={!!loadingSim || workers.length === 0}
            onClick={() => simulate('gas')}
          >
            <span className="sim-btn__icon" aria-hidden>
              {SIM_ICONS.gas}
            </span>
            <span className="sim-btn__label">Gas Leak</span>
          </button>
          <button
            type="button"
            className="sim-btn"
            disabled={!!loadingSim || workers.length === 0}
            onClick={() => simulate('heat')}
          >
            <span className="sim-btn__icon" aria-hidden>
              {SIM_ICONS.heat}
            </span>
            <span className="sim-btn__label">Heat Stress</span>
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
            <span className="sim-btn__label">SOS Pressed</span>
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
