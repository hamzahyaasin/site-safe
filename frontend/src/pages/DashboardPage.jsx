import { useCallback, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { useAlerts } from '../hooks/useAlerts.js'
import { useDashboardStats } from '../hooks/useDashboardStats.js'
import { useWorkers } from '../hooks/useWorkers.js'
import AlertFeed from '../components/dashboard/AlertFeed.jsx'
import DashboardCharts from '../components/dashboard/DashboardCharts.jsx'
import KpiStrip from '../components/dashboard/KpiStrip.jsx'
import WorkerStatusGrid from '../components/dashboard/WorkerStatusGrid.jsx'
import Button from '../components/ui/Button.jsx'
import { Select } from '../components/ui/Input.jsx'

export default function DashboardPage() {
  const { api } = useAuth()
  const { stats, loading: statsLoading, fetchStats } = useDashboardStats()
  const { workers, loading: workersLoading, highlightIds } = useWorkers()
  const {
    alerts,
    loading: alertsLoading,
    resolveAlert,
    newAlertIds,
    fetchAlerts,
  } = useAlerts({ is_resolved: 'false', ordering: '-timestamp' })

  const [workerId, setWorkerId] = useState('')
  const selectedWorkerId = workerId || (workers[0] ? String(workers[0].id) : '')
  const [loadingSim, setLoadingSim] = useState(null)
  const [toast, setToast] = useState(null)

  const showToast = useCallback((msg, type = 'success') => {
    setToast({ msg, type })
    window.setTimeout(() => setToast(null), 3500)
  }, [])

  async function simulate(kind) {
    if (!selectedWorkerId) {
      showToast('Select a worker first', 'error')
      return
    }
    const payloads = {
      fall: { alert_type: 'FALL', severity: 'CRITICAL', source: 'SIMULATED', worker_id: Number(selectedWorkerId) },
      gas: { alert_type: 'GAS_LEAK', severity: 'HIGH', source: 'SIMULATED', worker_id: Number(selectedWorkerId) },
      heat: { alert_type: 'HEAT_STRESS', severity: 'MEDIUM', source: 'SIMULATED', worker_id: Number(selectedWorkerId) },
      sos: { alert_type: 'SOS', severity: 'CRITICAL', source: 'SIMULATED', worker_id: Number(selectedWorkerId) },
    }
    setLoadingSim(kind)
    try {
      await api.post('alerts/simulate/', payloads[kind])
      showToast('Alert simulated successfully')
      await Promise.all([fetchStats(), fetchAlerts()])
    } catch (e) {
      showToast(e.response?.data?.detail || 'Failed to send alert', 'error')
    } finally {
      setLoadingSim(null)
    }
  }

  return (
    <div className="grid grid-cols-12 gap-4">
      <header className="col-span-12 mb-2">
        <h1 className="text-2xl font-semibold text-zinc-100">Safety Dashboard</h1>
        <p className="mt-1 text-sm text-zinc-500">Live site status — workers, compliance, and active incidents</p>
      </header>

      <KpiStrip stats={stats} loading={statsLoading} />

      <WorkerStatusGrid
        workers={workers}
        loading={workersLoading}
        highlightIds={highlightIds}
      />

      <AlertFeed
        alerts={alerts}
        loading={alertsLoading}
        onResolve={resolveAlert}
        newAlertIds={newAlertIds}
      />

      <DashboardCharts stats={stats} loading={statsLoading} />

      <section className="col-span-12 rounded-lg border border-zinc-800 bg-[#151821] p-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-zinc-100">IoT Vest Simulator</h2>
            <p className="text-xs text-zinc-500">Simulate smart vest events for testing</p>
          </div>
          <span className="rounded border border-zinc-700 px-2 py-0.5 text-[10px] text-zinc-500">
            Hardware offline
          </span>
        </div>
        <Select
          label="Target worker"
          value={selectedWorkerId}
          onChange={(e) => setWorkerId(e.target.value)}
          className="mb-4 max-w-xs"
          disabled={workers.length === 0}
        >
          {workers.length === 0 ? (
            <option>No workers</option>
          ) : (
            workers.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name} — {w.vest_id}
              </option>
            ))
          )}
        </Select>
        <div className="flex flex-wrap gap-2">
          {[
            { id: 'fall', label: 'Fall Detected', sev: 'CRITICAL' },
            { id: 'gas', label: 'Gas Leak', sev: 'HIGH' },
            { id: 'heat', label: 'Heat Stress', sev: 'MEDIUM' },
            { id: 'sos', label: 'SOS Pressed', sev: 'CRITICAL' },
          ].map((sim) => (
            <Button
              key={sim.id}
              variant="secondary"
              size="sm"
              disabled={!!loadingSim || workers.length === 0}
              onClick={() => simulate(sim.id)}
            >
              {loadingSim === sim.id ? 'Sending…' : sim.label}
              <span className="ml-1 text-[10px] text-zinc-500">{sim.sev}</span>
            </Button>
          ))}
        </div>
      </section>

      {toast ? (
        <div
          className={`fixed bottom-6 right-6 z-50 rounded-lg border px-4 py-3 text-sm shadow-lg ${
            toast.type === 'error'
              ? 'border-red-500/40 bg-red-500/10 text-red-300'
              : 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
          }`}
          role="status"
        >
          {toast.msg}
        </div>
      ) : null}
    </div>
  )
}
