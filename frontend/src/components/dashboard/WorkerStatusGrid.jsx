import { Link } from 'react-router-dom'
import Badge from '../ui/Badge.jsx'
import Card, { CardContent, CardDescription, CardHeader, CardTitle } from '../ui/Card.jsx'
import EmptyState from '../ui/EmptyState.jsx'
import Skeleton from '../ui/Skeleton.jsx'
import Tooltip from '../ui/Tooltip.jsx'
import {
  cn,
  deriveLastSeen,
  deriveWorkerVitals,
  formatTimestamp,
  getWorkerPresenceStatus,
  initials,
} from '../../lib/utils.js'

export default function WorkerStatusGrid({ workers, loading, highlightIds }) {
  return (
    <Card className="col-span-12 xl:col-span-8">
      <CardHeader>
        <CardTitle>Worker Status</CardTitle>
        <CardDescription>Live personnel on site with vest telemetry</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(240px,1fr))]">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-36 w-full" />
            ))}
          </div>
        ) : workers.length === 0 ? (
          <EmptyState
            title="No workers registered"
            description="Add workers in Vest Management to monitor site personnel."
          />
        ) : (
          <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(240px,1fr))]">
            {workers.map((worker) => {
              const lastSeen = deriveLastSeen(worker)
              const status = getWorkerPresenceStatus(worker, lastSeen)
              const vitals = deriveWorkerVitals(worker)
              const highlighted = highlightIds?.has(worker.id)
              const showVitals = worker.is_active && status.label === 'ACTIVE'

              return (
                <article
                  key={worker.id}
                  className={cn(
                    'rounded-lg border border-zinc-800 bg-zinc-900/30 p-3 transition-colors',
                    highlighted && 'animate-highlight animate-card-pulse',
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-zinc-800 text-sm font-semibold text-amber-400">
                      {initials(worker.name)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1 pr-1">
                          <Tooltip content={worker.name}>
                            <p className="text-sm font-medium leading-snug text-zinc-100">{worker.name}</p>
                          </Tooltip>
                          <p className="mt-0.5 font-mono text-xs text-zinc-500">{worker.vest_id}</p>
                        </div>
                        <Badge variant={status.variant} className="shrink-0">
                          {status.label}
                        </Badge>
                      </div>
                      <p className="mt-2 text-[11px] text-zinc-600">
                        Last seen {formatTimestamp(lastSeen)}
                      </p>
                      {worker.zone ? (
                        <p className="mt-0.5 text-[11px] text-zinc-500">{worker.zone}</p>
                      ) : null}
                    </div>
                  </div>
                  {showVitals ? (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      <VitalChip label="Temp" value={`${vitals.temp}°C`} />
                      <VitalChip label="HR" value={`${vitals.heartRate} bpm`} />
                      <VitalChip label="Gas" value={`${vitals.gasPpm} ppm`} warn={vitals.gasPpm > 8} />
                    </div>
                  ) : null}
                </article>
              )
            })}

            <Link
              to="/vests"
              className="flex min-h-[136px] flex-col items-center justify-center rounded-lg border border-dashed border-zinc-700 bg-zinc-900/20 p-4 text-zinc-500 transition-colors hover:border-amber-500/40 hover:bg-zinc-900/40 hover:text-amber-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500"
            >
              <span className="mb-2 flex h-8 w-8 items-center justify-center rounded-md border border-zinc-700 text-lg">
                +
              </span>
              <span className="text-sm font-medium">Register new worker</span>
            </Link>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function VitalChip({ label, value, warn }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-medium',
        warn
          ? 'border-amber-500/40 bg-amber-500/10 text-amber-400'
          : 'border-zinc-700 bg-zinc-800/50 text-zinc-400',
      )}
    >
      <span className="text-zinc-600">{label}</span>
      {value}
    </span>
  )
}
