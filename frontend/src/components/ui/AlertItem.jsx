import Badge from './Badge.jsx'
import Button from './Button.jsx'
import { IconAlertTriangle, IconCheck } from './icons.jsx'
import {
  alertSubject,
  alertTypeTitle,
  cn,
  formatTimestamp,
  severityBadgeVariant,
  severityStripeClass,
} from '../../lib/utils.js'

const SEVERITY_ICON = {
  CRITICAL: 'bg-red-500/10 text-red-400',
  HIGH: 'bg-orange-500/10 text-orange-400',
  MEDIUM: 'bg-yellow-500/10 text-yellow-400',
  LOW: 'bg-sky-500/10 text-sky-400',
}

export default function AlertItem({ alert, onResolve, resolving, isNew, compact = false }) {
  const who = alertSubject(alert)
  const where = [alert.vest_id, !compact && alert.camera_id].filter(Boolean).join(' · ')

  return (
    <div
      className={cn(
        'flex items-start gap-3 border-b border-l-2 border-b-zinc-800/70 px-4 py-3 transition-colors last:border-b-0 hover:bg-zinc-800/20',
        severityStripeClass(alert.severity),
        isNew && 'animate-slide-in bg-amber-500/5',
      )}
    >
      <span
        className={cn(
          'mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md',
          SEVERITY_ICON[alert.severity] || 'bg-zinc-800 text-zinc-400',
        )}
      >
        <IconAlertTriangle className="h-3.5 w-3.5" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-sm font-medium text-zinc-100">{alertTypeTitle(alert.alert_type)}</span>
          <Badge variant={severityBadgeVariant(alert.severity)}>{alert.severity}</Badge>
          {alert.source === 'SIMULATED' ? <Badge variant="neutral">Simulated</Badge> : null}
        </div>
        <p className="mt-1 break-words text-xs text-zinc-400">
          {who}
          {where ? <span className="font-mono text-zinc-500"> · {where}</span> : null}
        </p>
        {alert.description && !compact ? (
          <p className="mt-1 line-clamp-2 text-xs text-zinc-500">{alert.description}</p>
        ) : null}
        <p className="mt-1 text-[11px] text-zinc-500">{formatTimestamp(alert.timestamp)}</p>
      </div>
      {!alert.is_resolved && onResolve ? (
        <Button
          variant="secondary"
          size="xs"
          className="mt-0.5"
          loading={resolving}
          onClick={() => onResolve(alert.id)}
          aria-label={`Resolve ${alertTypeTitle(alert.alert_type)} alert`}
        >
          {resolving ? null : <IconCheck className="h-3 w-3" />}
          Resolve
        </Button>
      ) : null}
    </div>
  )
}
