import { useAuth } from '../context/AuthContext.jsx'
import { useAlerts } from '../hooks/useAlerts.js'
import IncidentLogTable from '../components/incidents/IncidentLogTable.jsx'
import Alert from '../components/ui/Alert.jsx'

export default function IncidentsPage() {
  const { canOperate } = useAuth()
  const { alerts, loading, error, resolveAlert, fetchAlerts } = useAlerts({ ordering: '-timestamp' })

  return (
    <div className="space-y-6">
      {error ? (
        <Alert>
          Could not load incidents. Check that the server is running, then{' '}
          <button type="button" className="font-semibold underline" onClick={() => fetchAlerts()}>
            try again
          </button>
          .
        </Alert>
      ) : null}
      <IncidentLogTable alerts={alerts} loading={loading} onResolve={canOperate ? resolveAlert : undefined} />
    </div>
  )
}
