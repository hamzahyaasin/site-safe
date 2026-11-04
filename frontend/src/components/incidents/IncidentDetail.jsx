import Badge from '../ui/Badge.jsx'
import AlertSnapshot from './AlertSnapshot.jsx'
import {
  displayCameraId,
  alertTypeTitle,
  formatDateTime,
  formatTimestamp,
  severityBadgeVariant,
  sourceLabel,
} from '../../lib/utils.js'

export default function IncidentDetail({ alert }) {
  if (!alert) return null

  return (
    <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-4">
      <DetailField label="Timestamp" value={formatTimestamp(alert.timestamp)} />
      <DetailField label="Worker" value={alert.worker_name || (alert.zone ? 'None (zone alert)' : '—')} />
      <DetailField label="Vest ID" value={alert.vest_id || '—'} mono />
      <DetailField label="Camera" value={displayCameraId(alert)} mono />
      {alert.zone_name ? <DetailField label="Zone" value={alert.zone_name} /> : null}
      <DetailField label="Type" value={alertTypeTitle(alert.alert_type)} />
      <DetailField
        label="Severity"
        value={<Badge variant={severityBadgeVariant(alert.severity)}>{alert.severity}</Badge>}
      />
      <DetailField label="Source" value={sourceLabel(alert.source)} />
      {alert.confidence != null ? (
        <DetailField label="Confidence" value={`${Math.round(alert.confidence * 100)}%`} />
      ) : null}
      {alert.model_version ? <DetailField label="Model" value={alert.model_version} mono /> : null}
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
      <div className="sm:col-span-2 lg:col-span-4">
        <DetailField label="Description" value={alert.description || 'No description provided.'} />
      </div>
      {alert.snapshot ? (
        <div className="sm:col-span-2 lg:col-span-4">
          <DetailField label="Evidence frame" value={<AlertSnapshot key={alert.id} alertId={alert.id} />} />
        </div>
      ) : null}
    </div>
  )
}

function DetailField({ label, value, mono }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">{label}</p>
      <div className={`mt-1 text-sm text-zinc-200 ${mono ? 'font-mono' : ''}`}>{value}</div>
    </div>
  )
}
