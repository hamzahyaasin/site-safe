import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../../context/AuthContext.jsx'
import Badge from '../ui/Badge.jsx'
import { cn } from '../../lib/utils.js'
import { useFeedback } from '../../context/FeedbackContext.jsx'

const SEVERITIES = ['CRITICAL', 'HIGH', 'MEDIUM']
const SEVERITY_VARIANT = { CRITICAL: 'critical', HIGH: 'high', MEDIUM: 'medium' }

function apiError(err, fallback) {
  const data = err?.response?.data
  if (data && typeof data === 'object') {
    return Object.entries(data)
      .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' ') : v}`)
      .join('; ')
  }
  return fallback
}

/**
 * The enlarged live view of one camera with its danger areas (FR-32).
 *
 * Areas are polygons in fractions of the picture (0-1), drawn by Admins by
 * clicking points on the live image; the camera raises a DANGER_AREA alert
 * when a person's feet are inside an active area. Safety Officers see the
 * areas but cannot change them (the API enforces the same).
 */
export default function CameraWithAreas({ cameraId, frameUrl, live }) {
  const { confirm } = useFeedback()
  const { api, isAdmin } = useAuth()
  const [areas, setAreas] = useState([])
  const [error, setError] = useState(null)
  const [draft, setDraft] = useState(null) // { points: [[x, y]], name, severity }
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('v1/camera-areas/', { params: { camera_id: cameraId } })
      setAreas(Array.isArray(data) ? data : data?.results || [])
    } catch (err) {
      setError(apiError(err, 'Could not load danger areas.'))
    }
  }, [api, cameraId])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async load when the camera changes
    void load()
  }, [load])

  function addPoint(e) {
    if (!draft) return
    const rect = e.currentTarget.getBoundingClientRect()
    const x = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
    const y = Math.min(1, Math.max(0, (e.clientY - rect.top) / rect.height))
    setDraft((d) => ({ ...d, points: [...d.points, [Number(x.toFixed(4)), Number(y.toFixed(4))]] }))
  }

  async function save() {
    setSaving(true)
    setError(null)
    try {
      await api.post('v1/camera-areas/', {
        camera_id: cameraId,
        name: draft.name,
        severity: draft.severity,
        polygon: draft.points,
      })
      setDraft(null)
      await load()
    } catch (err) {
      setError(apiError(err, 'Could not save the area.'))
    } finally {
      setSaving(false)
    }
  }

  async function toggle(area) {
    setError(null)
    try {
      await api.patch(`v1/camera-areas/${area.id}/`, { is_active: !area.is_active })
      await load()
    } catch (err) {
      setError(apiError(err, 'Could not update the area.'))
    }
  }

  async function remove(area) {
    const ok = await confirm({
      title: `Delete the danger area "${area.name}"?`,
      message: `People entering it on ${cameraId} will no longer raise an alert. Past alerts are kept.`,
      confirmLabel: 'Delete area',
    })
    if (!ok) return
    setError(null)
    try {
      await api.delete(`v1/camera-areas/${area.id}/`)
      await load()
    } catch (err) {
      setError(apiError(err, 'Could not delete the area.'))
    }
  }

  const canDraw = isAdmin && Boolean(frameUrl)

  return (
    <div className="grid gap-3 lg:grid-cols-[1fr_280px]">
      <div className="relative w-full overflow-hidden rounded bg-black">
        {frameUrl ? (
          <img
            src={frameUrl}
            alt={`Live view from ${cameraId}`}
            className={cn('block h-auto w-full', !live && 'opacity-40 grayscale')}
          />
        ) : (
          <div className="flex aspect-video items-center justify-center text-xs text-zinc-600">No live view</div>
        )}
        {frameUrl ? (
          <svg
            viewBox="0 0 1 1"
            preserveAspectRatio="none"
            className={cn('absolute inset-0 h-full w-full', draft && 'cursor-crosshair')}
            onClick={addPoint}
            role={draft ? 'application' : undefined}
            aria-label={draft ? 'Click to add points to the new danger area' : undefined}
          >
            {areas.map((a) => (
              <polygon
                key={a.id}
                points={a.polygon.map(([x, y]) => `${x},${y}`).join(' ')}
                fill={a.is_active ? 'rgba(245, 158, 11, 0.12)' : 'transparent'}
                stroke={a.is_active ? '#f59e0b' : '#71717a'}
                strokeWidth="2"
                strokeDasharray={a.is_active ? undefined : '6 6'}
                vectorEffect="non-scaling-stroke"
              />
            ))}
            {draft?.points.length ? (
              <polyline
                points={[...draft.points, ...(draft.points.length > 2 ? [draft.points[0]] : [])]
                  .map(([x, y]) => `${x},${y}`)
                  .join(' ')}
                fill={draft.points.length > 2 ? 'rgba(239, 68, 68, 0.2)' : 'none'}
                stroke="#ef4444"
                strokeWidth="2"
                vectorEffect="non-scaling-stroke"
              />
            ) : null}
            {draft?.points.map(([x, y], i) => (
              <circle key={i} cx={x} cy={y} r="0.006" fill="#ef4444" />
            ))}
          </svg>
        ) : null}
      </div>

      <div className="space-y-3 text-sm">
        <div>
          <p className="font-medium text-zinc-200">Danger areas</p>
          <p className="text-[11px] text-zinc-500">
            A person whose feet are inside an active area for 1 s raises a Danger area alert with a snapshot. Changes
            reach the camera within 15 s.
          </p>
        </div>

        {error ? <p className="text-xs text-red-400">{error}</p> : null}

        {areas.length === 0 && !draft ? <p className="text-xs text-zinc-500">No areas on this camera yet.</p> : null}
        <ul className="space-y-1.5">
          {areas.map((a) => (
            <li key={a.id} className="flex items-center gap-2 rounded border border-zinc-800 px-2 py-1.5">
              <span className={cn('min-w-0 flex-1 truncate', !a.is_active && 'text-zinc-500 line-through')}>{a.name}</span>
              <Badge variant={SEVERITY_VARIANT[a.severity] || 'neutral'}>{a.severity}</Badge>
              {isAdmin ? (
                <>
                  <button
                    type="button"
                    onClick={() => toggle(a)}
                    className="text-[11px] text-zinc-300 hover:text-zinc-100"
                    title={a.is_active ? 'Switch off while the hazard is not present' : 'Switch on'}
                  >
                    {a.is_active ? 'On' : 'Off'}
                  </button>
                  <button type="button" onClick={() => remove(a)} className="text-[11px] text-red-400 hover:text-red-300">
                    Delete
                  </button>
                </>
              ) : (
                <span className="text-[11px] text-zinc-500">{a.is_active ? 'On' : 'Off'}</span>
              )}
            </li>
          ))}
        </ul>

        {isAdmin && !draft ? (
          <button
            type="button"
            disabled={!canDraw}
            onClick={() => setDraft({ points: [], name: '', severity: 'HIGH' })}
            className="w-full rounded border border-amber-500/40 px-2 py-1.5 text-amber-400 hover:bg-amber-500/10 disabled:opacity-40"
            title={canDraw ? undefined : 'Start the camera to draw on its picture'}
          >
            Draw a danger area
          </button>
        ) : null}

        {draft ? (
          <div className="space-y-2 rounded border border-red-500/30 p-2">
            <p className="text-[11px] text-zinc-400">
              Click the picture to add corners ({draft.points.length} so far, at least 3). Draw where people stand: the
              area is checked against their feet.
            </p>
            <input
              value={draft.name}
              onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
              placeholder="Name, e.g. Crane swing"
              maxLength={60}
              className="w-full rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm text-zinc-100"
              aria-label="Area name"
            />
            <select
              value={draft.severity}
              onChange={(e) => setDraft((d) => ({ ...d, severity: e.target.value }))}
              className="w-full rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm text-zinc-100"
              aria-label="Alert severity"
            >
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setDraft((d) => ({ ...d, points: d.points.slice(0, -1) }))}
                disabled={!draft.points.length}
                className="rounded border border-zinc-700 px-2 py-1 text-[11px] text-zinc-300 disabled:opacity-40"
              >
                Undo point
              </button>
              <button
                type="button"
                onClick={() => setDraft(null)}
                className="rounded border border-zinc-700 px-2 py-1 text-[11px] text-zinc-300"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={save}
                disabled={saving || draft.points.length < 3 || !draft.name.trim()}
                className="ml-auto rounded bg-amber-500 px-2 py-1 text-[11px] font-medium text-zinc-900 disabled:opacity-40"
              >
                {saving ? 'Saving…' : 'Save area'}
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
