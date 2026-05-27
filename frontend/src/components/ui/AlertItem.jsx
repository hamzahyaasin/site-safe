import Badge from './Badge.jsx'
import Button from './Button.jsx'
import {
  cameraIdFromSource,
  cn,
  formatAlertType,
  formatTimestamp,
  severityBadgeVariant,
  severityStripeClass,
} from '../../lib/utils.js'

function SeverityIcon({ severity }) {
  const colors = {
    CRITICAL: 'text-red-400',
    HIGH: 'text-orange-400',
    MEDIUM: 'text-yellow-400',
    LOW: 'text-blue-400',
  }
  return (
    <svg
      className={cn('h-4 w-4 shrink-0', colors[severity] || 'text-zinc-500')}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden
    >
      <path d="M10.29 3.86L1.82 18h20.36L13.71 3.86 10.29 3.86z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  )
}

export default function AlertItem({
  alert,
  onResolve,
  resolving,
  isNew,
  compact = false,
}) {
  return (
    <div
      className={cn(
        'flex items-start gap-3 border-b border-zinc-800/80 border-l-[3px] px-3 py-3 last:border-b-0',
        severityStripeClass(alert.severity),
        isNew && 'animate-slide-in bg-amber-500/5',
      )}
    >
      <SeverityIcon severity={alert.severity} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-zinc-200">
            {formatAlertType(alert.alert_type)}
          </span>
          <Badge variant={severityBadgeVariant(alert.severity)}>{alert.severity}</Badge>
        </div>
        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-zinc-500">
          <span>{alert.worker_name || 'Unknown worker'}</span>
          <span className="font-mono">{alert.vest_id || '—'}</span>
          {!compact ? (
            <span className="font-mono">{cameraIdFromSource(alert.source)}</span>
          ) : null}
        </div>
        <p className="mt-1 text-[11px] text-zinc-600">{formatTimestamp(alert.timestamp)}</p>
      </div>
      {!alert.is_resolved && onResolve ? (
        <Button
          variant="ghost"
          size="sm"
          className="shrink-0 text-xs"
          disabled={resolving}
          onClick={() => onResolve(alert.id)}
        >
          {resolving ? '…' : 'Resolve'}
        </Button>
      ) : null}
    </div>
  )
}
