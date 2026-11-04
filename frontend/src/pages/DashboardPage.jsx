import { useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { apiErrorText, useFeedback } from '../context/FeedbackContext.jsx'
import { useAlerts } from '../hooks/useAlerts.js'
import { useDashboardStats } from '../hooks/useDashboardStats.js'
import { useWorkers } from '../hooks/useWorkers.js'
import AlertFeed from '../components/dashboard/AlertFeed.jsx'
import DashboardCharts from '../components/dashboard/DashboardCharts.jsx'
import KpiStrip from '../components/dashboard/KpiStrip.jsx'
import SiteMapCard from '../components/dashboard/SiteMapCard.jsx'
import WorkerStatusGrid from '../components/dashboard/WorkerStatusGrid.jsx'
import Badge from '../components/ui/Badge.jsx'
import Button from '../components/ui/Button.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import { Select } from '../components/ui/Input.jsx'

export default function DashboardPage() {
  const { api, canOperate } = useAuth()
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
  const { toast } = useFeedback()

  async function simulate(kind) {
    if (!selectedWorkerId) {
      toast('Select a worker first', 'error')
      return
    }
    const payloads = {
      ppe: { alert_type: 'PPE_VIOLATION', severity: 'HIGH', source: 'SIMULATED', worker_id: Number(selectedWorkerId) },
      zone_breach: { alert_type: 'ZONE_BREACH', severity: 'HIGH', source: 'SIMULATED', worker_id: Number(selectedWorkerId) },
      inactivity: { alert_type: 'INACTIVITY', severity: 'MEDIUM', source: 'SIMULATED', worker_id: Number(selectedWorkerId) },
      sos: { alert_type: 'SOS', severity: 'CRITICAL', source: 'SIMULATED', worker_id: Number(selectedWorkerId) },
      vehicle_proximity: { alert_type: 'VEHICLE_PROXIMITY', severity: 'CRITICAL', source: 'SIMULATED', worker_id: Number(selectedWorkerId) },
      fall: { alert_type: 'FALL', severity: 'CRITICAL', source: 'SIMULATED', worker_id: Number(selectedWorkerId) },
      fire: { alert_type: 'FIRE', severity: 'CRITICAL', source: 'SIMULATED', worker_id: Number(selectedWorkerId) },
      danger_area: { alert_type: 'DANGER_AREA', severity: 'CRITICAL', source: 'SIMULATED', worker_id: Number(selectedWorkerId) },
      gas: { alert_type: 'GAS', severity: 'CRITICAL', source: 'SIMULATED', worker_id: Number(selectedWorkerId) },
    }
    setLoadingSim(kind)
    try {
      await api.post('alerts/simulate/', payloads[kind])
      toast('Simulated alert sent. It appears in the feed and is labelled SIMULATED.')
      await Promise.all([fetchStats(), fetchAlerts({ quiet: true })])
    } catch (e) {
      toast(apiErrorText(e, 'Failed to send alert'), 'error')
    } finally {
      setLoadingSim(null)
    }
  }

  return (
    <div className="grid grid-cols-12 gap-4">
      <PageHeader
        className="col-span-12 mb-2"
        title="Safety Dashboard"
        description="Live site status — worker presence and open incidents"
      />

      <KpiStrip stats={stats} loading={statsLoading} />

      <WorkerStatusGrid
        className="col-span-12 xl:col-span-8"
        workers={workers}
        loading={workersLoading}
        highlightIds={highlightIds}
        canAdd={canOperate}
      />

      <AlertFeed
        alerts={alerts}
        loading={alertsLoading}
        onResolve={canOperate ? resolveAlert : undefined}
        newAlertIds={newAlertIds}
      />

      <SiteMapCard />

      <DashboardCharts stats={stats} loading={statsLoading} />

      {canOperate ? (
        <section className="col-span-12 rounded-xl border border-dashed border-zinc-700/80 bg-[#151821]/60 p-4 sm:p-5">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-zinc-100">Event Simulator</h2>
              <p className="mt-0.5 text-xs text-zinc-500">
                Creates test alerts marked SIMULATED; they are counted separately from real observations
              </p>
            </div>
            <Badge variant="neutral">Test data</Badge>
          </div>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
            <Select
              label="Target worker"
              value={selectedWorkerId}
              onChange={(e) => setWorkerId(e.target.value)}
              className="w-full lg:w-64"
              disabled={workers.length === 0}
            >
              {workers.length === 0 ? (
                <option>No workers</option>
              ) : (
                workers.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name}
                    {w.vest_id ? ` — ${w.vest_id}` : ''}
                  </option>
                ))
              )}
            </Select>
            <div className="flex flex-1 flex-wrap gap-2">
              {SIMULATIONS.map((sim) => (
                <Button
                  key={sim.id}
                  variant="secondary"
                  size="sm"
                  loading={loadingSim === sim.id}
                  disabled={!!loadingSim || workers.length === 0}
                  onClick={() => simulate(sim.id)}
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${SEVERITY_DOT[sim.sev]}`} aria-hidden />
                  {sim.label}
                  <span className="sr-only">({sim.sev.toLowerCase()} severity)</span>
                </Button>
              ))}
            </div>
          </div>
        </section>
      ) : null}
    </div>
  )
}

const SEVERITY_DOT = { CRITICAL: 'bg-red-400', HIGH: 'bg-orange-400', MEDIUM: 'bg-yellow-400' }

const SIMULATIONS = [
  { id: 'ppe', label: 'PPE Violation', sev: 'HIGH' },
  { id: 'zone_breach', label: 'Zone Breach', sev: 'HIGH' },
  { id: 'inactivity', label: 'Inactivity', sev: 'MEDIUM' },
  { id: 'sos', label: 'SOS Pressed', sev: 'CRITICAL' },
  { id: 'vehicle_proximity', label: 'Vehicle Proximity', sev: 'CRITICAL' },
  { id: 'fall', label: 'Fall', sev: 'CRITICAL' },
  { id: 'fire', label: 'Fire', sev: 'CRITICAL' },
  { id: 'danger_area', label: 'Danger area', sev: 'CRITICAL' },
  { id: 'gas', label: 'Gas', sev: 'CRITICAL' },
]
