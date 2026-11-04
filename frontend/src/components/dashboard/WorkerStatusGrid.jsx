import { Link } from 'react-router-dom'
import Badge from '../ui/Badge.jsx'
import Button from '../ui/Button.jsx'
import { IconClock, IconPencil, IconPlus } from '../ui/icons.jsx'
import Card, { CardContent, CardDescription, CardHeader, CardTitle } from '../ui/Card.jsx'
import EmptyState from '../ui/EmptyState.jsx'
import Skeleton from '../ui/Skeleton.jsx'
import Tooltip from '../ui/Tooltip.jsx'
import { cn, describeLocation, formatTimestamp, getWorkerPresence, initials } from '../../lib/utils.js'

/** Worker cards. Presence and location come from vest GPS and camera badge
 * sightings, battery from the vest; ``onEdit`` (Workers page) adds an edit
 * action per card and ``canAdd`` shows the register tile. */
export default function WorkerStatusGrid({
  workers,
  loading,
  highlightIds,
  onEdit,
  onAdd,
  onTimeline,
  canAdd = false,
  className,
  title = 'Worker Status',
  description = 'Location from camera badge sightings and vest GPS',
}) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(min(100%,280px),1fr))]">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-36 w-full" />
            ))}
          </div>
        ) : workers.length === 0 ? (
          <EmptyState
            title="No workers registered"
            description="Register workers and assign them a vest to track presence."
            action={
              canAdd ? (
                onAdd ? (
                  <Button variant="primary" size="sm" onClick={onAdd}>
                    <IconPlus className="h-3.5 w-3.5" />
                    Register worker
                  </Button>
                ) : (
                  <Link to="/workers?new=1" className="text-sm font-medium text-amber-400 hover:text-amber-300">
                    Register a worker
                  </Link>
                )
              ) : null
            }
          />
        ) : (
          <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(min(100%,280px),1fr))]">
            {workers.map((worker) => {
              const presence = getWorkerPresence(worker)
              const vest = worker.smart_vest
              const highlighted = highlightIds?.has(worker.id)

              return (
                <article
                  key={worker.id}
                  className={cn(
                    'flex flex-col rounded-lg border border-zinc-800 bg-zinc-900/40 transition-colors hover:border-zinc-700',
                    highlighted && 'animate-highlight animate-card-pulse',
                    !worker.is_active && 'opacity-60',
                  )}
                >
                  <div className="flex items-start gap-3 p-3.5">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-zinc-800 text-sm font-semibold text-amber-300 ring-1 ring-zinc-700">
                      {initials(worker.name)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <Tooltip content={worker.name}>
                        <p className="truncate text-sm font-semibold text-zinc-100">{worker.name}</p>
                      </Tooltip>
                      <p className="mt-0.5 truncate text-xs text-zinc-500">
                        {worker.role ? (
                          <>
                            {worker.role}
                            <span className="text-zinc-700"> · </span>
                          </>
                        ) : null}
                        <span className="font-mono">{worker.vest_id || 'No vest'}</span>
                      </p>
                    </div>
                    <Badge variant={presence.variant} dot className="shrink-0">
                      {presence.label}
                    </Badge>
                  </div>
                  <div className="space-y-0.5 px-3.5 pb-3 text-xs">
                    <p className={cn(worker.location?.current ? 'font-medium text-emerald-400' : 'text-zinc-400')}>
                      {describeLocation(worker) ||
                        (vest ? 'Vest has not reported a position yet' : 'No camera has read this badge yet')}
                    </p>
                    {presence.lastSeen ? <p className="text-zinc-500">Seen {formatTimestamp(presence.lastSeen)}</p> : null}
                    <p className="text-zinc-500">Assigned zone: {worker.zone_name || 'none'}</p>
                  </div>
                  <div className="mt-auto flex flex-wrap items-center gap-1.5 border-t border-zinc-800/80 px-3.5 py-2.5">
                    {vest ? (
                      <Chip
                        label="Battery"
                        value={vest.battery_level === null ? 'unknown' : `${vest.battery_level}%`}
                        warn={vest.battery_level !== null && vest.battery_level < 20}
                      />
                    ) : null}
                    {vest?.latitude !== null && vest?.latitude !== undefined ? (
                      <Chip label="GPS" value={`${vest.latitude.toFixed(5)}, ${vest.longitude.toFixed(5)}`} />
                    ) : null}
                    <div className="ml-auto flex gap-1">
                      {onTimeline ? (
                        <Button variant="ghost" size="xs" onClick={() => onTimeline(worker)}>
                          <IconClock className="h-3.5 w-3.5" />
                          Timeline
                        </Button>
                      ) : null}
                      {onEdit ? (
                        <Button variant="ghost" size="xs" className="text-amber-300 hover:text-amber-200" onClick={() => onEdit(worker)}>
                          <IconPencil className="h-3.5 w-3.5" />
                          Edit
                        </Button>
                      ) : null}
                    </div>
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
  'flex min-h-[148px] flex-col items-center justify-center rounded-lg border border-dashed border-zinc-700 bg-zinc-900/20 p-4 text-zinc-500 transition-colors hover:border-amber-500/40 hover:bg-zinc-900/40 hover:text-amber-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500'

function AddTileContent() {
  return (
    <>
      <span className="mb-2 flex h-9 w-9 items-center justify-center rounded-full border border-dashed border-current">
        <IconPlus className="h-4 w-4" />
      </span>
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
