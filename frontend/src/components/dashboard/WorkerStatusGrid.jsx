import { Link } from 'react-router-dom'
import Badge from '../ui/Badge.jsx'
import Card, { CardContent, CardDescription, CardHeader, CardTitle } from '../ui/Card.jsx'
import EmptyState from '../ui/EmptyState.jsx'
import Skeleton from '../ui/Skeleton.jsx'
import Tooltip from '../ui/Tooltip.jsx'
import { cn, describeLocation, formatGas, formatTimestamp, getWorkerPresence, initials } from '../../lib/utils.js'

/** Worker cards. Presence and location come from vest GPS and camera badge
 * sightings, battery from the vest; ``onEdit`` (Workers page) adds an edit
 * action per card and ``canAdd`` shows the register tile. */
export default function WorkerStatusGrid({ workers, loading, highlightIds, onEdit, onAdd, onTimeline, canAdd = false }) {
  return (
    <Card className="col-span-12 xl:col-span-8">
      <CardHeader>
        <CardTitle>Worker Status</CardTitle>
        <CardDescription>Location from camera badge sightings and vest GPS</CardDescription>
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
            description="Register workers on the Workers page and assign them a vest to track presence."
          />
        ) : (
          <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(240px,1fr))]">
            {workers.map((worker) => {
              const presence = getWorkerPresence(worker)
              const vest = worker.smart_vest
              const highlighted = highlightIds?.has(worker.id)

              return (
                <article
                  key={worker.id}
                  className={cn(
                    'rounded-lg border border-zinc-800 bg-zinc-900/30 p-3 transition-colors',
                    highlighted && 'animate-highlight animate-card-pulse',
                    !worker.is_active && 'opacity-60',
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
                          <p className="mt-0.5 font-mono text-xs text-zinc-500">
                            {worker.vest_id || 'No vest assigned'}
                          </p>
                        </div>
                        <Badge variant={presence.variant} className="shrink-0">
                          {presence.label}
                        </Badge>
                      </div>
                      <p
                        className={cn(
                          'mt-2 text-[11px]',
                          worker.location?.current ? 'font-medium text-emerald-400' : 'text-zinc-500',
                        )}
                      >
                        {describeLocation(worker) ||
                          (vest ? 'Vest has not reported a position yet' : 'No camera has read this badge yet')}
                      </p>
                      {presence.lastSeen ? (
                        <p className="mt-0.5 text-[11px] text-zinc-600">Seen {formatTimestamp(presence.lastSeen)}</p>
                      ) : null}
                      <p className="mt-0.5 text-[11px] text-zinc-500">
                        Assigned zone: {worker.zone_name || 'none'}
                        {worker.role ? ` · ${worker.role}` : ''}
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-1.5">
                    {vest ? (
                      <Chip
                        label="Battery"
                        value={vest.battery_level === null ? 'unknown' : `${vest.battery_level}%`}
                        warn={vest.battery_level !== null && vest.battery_level < 20}
                      />
                    ) : null}
                    {formatGas(vest) ? <Chip label="Gas" value={formatGas(vest)} warn={vest.gas_over_limit} /> : null}
                    {vest?.latitude !== null && vest?.latitude !== undefined ? (
                      <Chip label="GPS" value={`${vest.latitude.toFixed(5)}, ${vest.longitude.toFixed(5)}`} />
                    ) : null}
                    {onTimeline ? (
                      <button
                        type="button"
                        onClick={() => onTimeline(worker)}
                        className="ml-auto rounded px-2 py-0.5 text-[11px] text-zinc-300 hover:bg-zinc-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500"
                      >
                        Timeline
                      </button>
                    ) : null}
                    {onEdit ? (
                      <button
                        type="button"
                        onClick={() => onEdit(worker)}
                        className={`${onTimeline ? '' : 'ml-auto '}rounded px-2 py-0.5 text-[11px] text-amber-400 hover:bg-amber-500/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500`}
                      >
                        Edit
                      </button>
                    ) : null}
                  </div>
                </article>
              )
            })}

            {canAdd ? (
              onAdd ? (
                <button type="button" onClick={onAdd} className={ADD_TILE}>
                  <AddTileContent />
                </button>
              ) : (
                <Link to="/workers?new=1" className={ADD_TILE}>
                  <AddTileContent />
                </Link>
              )
            ) : null}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

const ADD_TILE =
  'flex min-h-[136px] flex-col items-center justify-center rounded-lg border border-dashed border-zinc-700 bg-zinc-900/20 p-4 text-zinc-500 transition-colors hover:border-amber-500/40 hover:bg-zinc-900/40 hover:text-amber-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500'

function AddTileContent() {
  return (
    <>
      <span className="mb-2 flex h-8 w-8 items-center justify-center rounded-md border border-zinc-700 text-lg">+</span>
      <span className="text-sm font-medium">Register new worker</span>
    </>
  )
}

function Chip({ label, value, warn }) {
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
