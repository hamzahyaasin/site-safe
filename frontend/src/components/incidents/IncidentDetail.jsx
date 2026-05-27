import Badge from '../ui/Badge.jsx'
import {
  cameraIdFromSource,
  formatAlertType,
  formatDateTime,
  formatTimestamp,
  severityBadgeVariant,
  sourceLabel,
} from '../../lib/utils.js'

export default function IncidentDetail({ alert }) {
  if (!alert) return null

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <DetailField label="Timestamp" value={formatTimestamp(alert.timestamp)} />
      <DetailField label="Worker" value={alert.worker_name || '—'} />
      <DetailField label="Vest ID" value={alert.vest_id || '—'} mono />
      <DetailField label="Camera" value={cameraIdFromSource(alert.source)} mono />
      <DetailField label="Type" value={formatAlertType(alert.alert_type)} />
      <DetailField
        label="Severity"
        value={<Badge variant={severityBadgeVariant(alert.severity)}>{alert.severity}</Badge>}
      />
      <DetailField label="Source" value={sourceLabel(alert.source)} />
      <DetailField
        label="Status"
        value={
          alert.is_resolved ? (
            <Badge variant="success">Resolved</Badge>
          ) : (
            <Badge variant="medium">Open</Badge>
          )
        }
      />
      {alert.resolved_at ? (
        <DetailField label="Resolved at" value={formatDateTime(alert.resolved_at)} />
      ) : null}
      <div className="sm:col-span-2">
        <DetailField label="Description" value={alert.description || 'No description provided.'} />
      </div>
    </div>
  )
}

function DetailField({ label, value, mono }) {
  return (
    <div>
      <p className="text-[10px] font-medium uppercase tracking-wide text-zinc-600">{label}</p>
      <div className={`mt-1 text-sm text-zinc-300 ${mono ? 'font-mono' : ''}`}>{value}</div>
    </div>
  )
}
