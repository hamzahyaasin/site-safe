import { useAlerts } from '../hooks/useAlerts.js'
import IncidentLogTable from '../components/incidents/IncidentLogTable.jsx'

export default function IncidentsPage() {
  const { alerts, loading, resolveAlert } = useAlerts({ ordering: '-timestamp' })

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-zinc-100">Incident Log</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Full audit trail of safety incidents from cameras, vests, and simulations
        </p>
      </header>
      <IncidentLogTable alerts={alerts} loading={loading} onResolve={resolveAlert} />
    </div>
  )
}
