import { useState } from 'react'
import { cameraStatus } from '../../hooks/useCameraMap.js'
import { cn } from '../../lib/utils.js'
import { useFeedback } from '../../context/FeedbackContext.jsx'

const DOT = { alerting: 'bg-red-500', live: 'bg-emerald-500', offline: 'bg-zinc-500' }
const COMPASS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']

function compass(degrees) {
  return COMPASS[Math.round(degrees / 45) % 8]
}

function apiError(err) {
  const data = err?.response?.data
  if (data && typeof data === 'object') {
    return Object.entries(data)
      .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' ') : v}`)
      .join('; ')
  }
  return 'Could not save the camera position.'
}

function Slider({ label, value, min, max, step, unit, onChange, hint }) {
  return (
    <label className="block text-[11px] text-zinc-400">
      <span className="flex justify-between">
        <span>{label}</span>
        <span className="font-mono text-zinc-200">
          {value}
          {unit}
          {hint ? ` ${hint}` : ''}
        </span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 w-full accent-amber-500"
      />
    </label>
  )
}

/**
 * Cameras on the site map (FR-33): every known camera with its live status,
 * and for Admins the controls to place, move or remove it. Placing works on
 * the map above: click where the camera is mounted, then turn it and set
 * how wide and how far it sees; the view cone follows on the map.
 */
export default function CameraPlacementPanel({ cameras, alerting, draft, setDraft, place, unplace, isAdmin }) {
  const { confirm } = useFeedback()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  function start(camera) {
    setError(null)
    setDraft({
      camera_id: camera.camera_id,
      latitude: camera.placement?.latitude ?? null,
      longitude: camera.placement?.longitude ?? null,
      heading: camera.placement?.heading ?? 0,
      field_of_view: camera.placement?.field_of_view ?? 70,
      view_range_m: camera.placement?.view_range_m ?? 30,
    })
  }

  async function save() {
    setSaving(true)
    setError(null)
    try {
      const { camera_id: cameraId, ...placement } = draft
      await place(cameraId, placement)
      setDraft(null)
    } catch (err) {
      setError(apiError(err))
    } finally {
      setSaving(false)
    }
  }

  async function remove(camera) {
    const ok = await confirm({
      title: `Take ${camera.camera_id} off the map?`,
      message: 'Its alerts and live view are not affected; only its position and view cone are removed.',
      confirmLabel: 'Remove from map',
    })
    if (!ok) return
    setError(null)
    try {
      await unplace(camera.camera_id)
    } catch (err) {
      setError(apiError(err))
    }
  }

  const set = (field) => (value) => setDraft((d) => ({ ...d, [field]: value }))

  return (
    <div className="space-y-3 text-sm">
      {error ? <p className="text-xs text-red-400">{error}</p> : null}

      {draft ? (
        <div className="space-y-2.5 rounded border border-amber-500/40 p-3">
          <p className="text-xs text-zinc-300">
            {draft.latitude == null ? (
              <>
                Click the map where <span className="font-mono">{draft.camera_id}</span> is mounted.
              </>
            ) : (
              <>
                <span className="font-mono">{draft.camera_id}</span> at {draft.latitude.toFixed(5)},{' '}
                {draft.longitude.toFixed(5)}. Click the map again to move it.
              </>
            )}
          </p>
          <Slider label="Facing" value={draft.heading} min={0} max={355} step={5} unit="°" hint={compass(draft.heading)} onChange={set('heading')} />
          <Slider label="View angle" value={draft.field_of_view} min={20} max={150} step={5} unit="°" onChange={set('field_of_view')} />
          <Slider label="Range" value={draft.view_range_m} min={5} max={150} step={5} unit=" m" onChange={set('view_range_m')} />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setDraft(null)}
              className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-300 hover:border-zinc-500"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={save}
              disabled={saving || draft.latitude == null}
              className="ml-auto rounded bg-amber-500 px-3 py-1 text-xs font-medium text-zinc-900 disabled:opacity-40"
            >
              {saving ? 'Saving…' : 'Save position'}
            </button>
          </div>
        </div>
      ) : null}

      {cameras.length === 0 ? (
        <p className="text-xs text-zinc-500">No cameras yet. Assign camera ids to a zone, or start a camera.</p>
      ) : (
        <ul className="divide-y divide-zinc-800 rounded border border-zinc-800">
          {cameras.map((camera) => {
            const status = cameraStatus(camera, alerting)
            const editing = draft?.camera_id === camera.camera_id
            return (
              <li key={camera.camera_id} className={cn('flex items-center gap-2 px-3 py-2', editing && 'bg-amber-500/5')}>
                <span className={cn('h-2 w-2 shrink-0 rounded-full', DOT[status])} title={status} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate">
                    <span className="font-mono text-zinc-100">{camera.camera_id}</span>
                    <span className="ml-2 text-xs text-zinc-500">{camera.zone || 'No zone'}</span>
                  </span>
                  <span className="block text-[11px] text-zinc-500">
                    <span className={camera.placement ? undefined : 'text-amber-400/80'}>
                      {camera.placement ? `On map, facing ${compass(camera.placement.heading)}` : 'Not on map'}
                    </span>
                    {camera.people_in_view != null ? ` · ${camera.people_in_view} in view` : ''}
                  </span>
                </span>
                {isAdmin && !draft ? (
                  <>
                    <button type="button" onClick={() => start(camera)} className="text-[11px] text-amber-400 hover:text-amber-300">
                      {camera.placement ? 'Move' : 'Place'}
                    </button>
                    {camera.placement ? (
                      <button type="button" onClick={() => remove(camera)} className="text-[11px] text-red-400 hover:text-red-300">
                        Remove
                      </button>
                    ) : null}
                  </>
                ) : null}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
