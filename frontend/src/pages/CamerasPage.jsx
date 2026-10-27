import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import Badge from '../components/ui/Badge.jsx'
import CameraWithAreas from '../components/cameras/DangerAreas.jsx'
import Card from '../components/ui/Card.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useCameraFeed } from '../hooks/useCameraFeed.js'
import { cn } from '../lib/utils.js'

const LIST_REFRESH_MS = 10000
// Matches the server's LIVE_OFFLINE_AFTER_SECONDS.
const OFFLINE_AFTER_MS = 5000

function ago(ms) {
  if (ms == null) return 'never'
  const s = Math.round(ms / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.round(s / 60)} min ago`
  return `${Math.round(s / 3600)} h ago`
}

export default function CamerasPage() {
  const { api, canOperate, role } = useAuth()
  const allowed = Boolean(role && canOperate)
  const { frames, status } = useCameraFeed(allowed)
  const [cameras, setCameras] = useState([])
  const [liveViewEnabled, setLiveViewEnabled] = useState(true)
  const [error, setError] = useState(null)
  // The enlarged camera is in the address (?camera=CAM-01), so the site map can link to it.
  const [params, setParams] = useSearchParams()
  const selected = params.get('camera')
  const setSelected = useCallback(
    (cameraId) => setParams(cameraId ? { camera: cameraId } : {}, { replace: true }),
    [setParams],
  )
  const [now, setNow] = useState(() => Date.now())

  const loadCameras = useCallback(async () => {
    try {
      const { data } = await api.get('v1/cameras/')
      setCameras(data.cameras || [])
      setLiveViewEnabled(data.live_view_enabled !== false)
      setError(null)
    } catch {
      setError('Could not load the camera list.')
    }
  }, [api])

  useEffect(() => {
    if (!allowed) return undefined
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async load on mount and on a timer
    void loadCameras()
    const list = window.setInterval(loadCameras, LIST_REFRESH_MS)
    const tick = window.setInterval(() => setNow(Date.now()), 1000)
    return () => {
      window.clearInterval(list)
      window.clearInterval(tick)
    }
  }, [allowed, loadCameras])

  useEffect(() => {
    if (!selected) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') setSelected(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected, setSelected])

  // Cameras from the server list, plus any camera that started streaming since it was fetched.
  const tiles = useMemo(() => {
    const byId = new Map(cameras.map((c) => [c.camera_id, c]))
    for (const id of Object.keys(frames)) {
      if (!byId.has(id)) byId.set(id, { camera_id: id, zone: null, last_frame_at: null })
    }
    return [...byId.values()]
      .map((c) => {
        const frame = frames[c.camera_id]
        const lastMs = frame ? frame.at : c.last_frame_at ? Date.parse(c.last_frame_at) : null
        return { ...c, frame, sinceMs: lastMs == null ? null : now - lastMs, live: Boolean(frame && now - frame.at < OFFLINE_AFTER_MS) }
      })
      .sort((a, b) => Number(b.live) - Number(a.live) || a.camera_id.localeCompare(b.camera_id))
  }, [cameras, frames, now])

  if (role && !canOperate) {
    return (
      <div className="space-y-6">
        <header>
          <h1 className="text-2xl font-semibold text-zinc-100">Cameras</h1>
          <p className="mt-1 text-sm text-zinc-500">Live camera views require the Safety Officer or Admin role.</p>
        </header>
      </div>
    )
  }

  const liveCount = tiles.filter((t) => t.live).length
  const focused = selected ? tiles.find((t) => t.camera_id === selected) : null

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100">Cameras</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Live view from every camera running the detection pipeline, with its detections drawn in. Frames are not
            recorded.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span className={cn('h-2 w-2 rounded-full', status === 'live' ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse')} />
          {status === 'live' ? `${liveCount} of ${tiles.length} live` : 'Connecting to live view…'}
        </div>
      </header>

      {!liveViewEnabled ? (
        <p className="rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-300">
          Live view is turned off on the server (LIVE_VIEW_ENABLED=False).
        </p>
      ) : null}
      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      {tiles.length === 0 ? (
        <Card className="px-4 py-10 text-center text-sm text-zinc-500">
          No cameras yet. Start the pipeline with a camera device token (ai-module/inference.py), or assign camera ids to a
          zone.
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {tiles.map((t) => (
            <CameraTile key={t.camera_id} tile={t} onOpen={() => setSelected(t.camera_id)} />
          ))}
        </div>
      )}

      {focused ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={`Camera ${focused.camera_id}`}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setSelected(null)}
        >
          <div className="max-h-full w-full max-w-6xl overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="mb-2 flex items-center justify-between text-sm text-zinc-300">
              <TileLabel tile={focused} />
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-300 hover:border-zinc-500"
              >
                Close (Esc)
              </button>
            </div>
            <CameraWithAreas cameraId={focused.camera_id} frameUrl={focused.frame?.url} live={focused.live} />
          </div>
        </div>
      ) : null}
    </div>
  )
}

function CameraTile({ tile, onOpen }) {
  return (
    <Card className="overflow-hidden">
      <button
        type="button"
        onClick={onOpen}
        className="block w-full text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500"
        aria-label={`Open camera ${tile.camera_id}`}
      >
        <Frame tile={tile} />
        <div className="flex items-center justify-between gap-2 px-3 py-2 text-sm">
          <TileLabel tile={tile} />
        </div>
      </button>
    </Card>
  )
}

function TileLabel({ tile }) {
  return (
    <>
      <span className="min-w-0 truncate">
        <span className="font-mono text-zinc-100">{tile.camera_id}</span>
        <span className="ml-2 text-xs text-zinc-500">{tile.zone || 'No zone'}</span>
      </span>
      {tile.live ? (
        <Badge variant="success">Live</Badge>
      ) : (
        <span className="shrink-0 text-xs text-zinc-500">Offline · {ago(tile.sinceMs)}</span>
      )}
    </>
  )
}

function Frame({ tile }) {
  return (
    <div className="relative aspect-video w-full bg-black">
      {tile.frame ? (
        <img
          src={tile.frame.url}
          alt={`Live view from ${tile.camera_id}`}
          className={cn('h-full w-full object-contain', !tile.live && 'opacity-40 grayscale')}
        />
      ) : (
        <div className="flex h-full items-center justify-center text-xs text-zinc-600">No live view</div>
      )}
    </div>
  )
}
