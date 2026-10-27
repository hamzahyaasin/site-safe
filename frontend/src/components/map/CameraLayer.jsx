import { useCallback, useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import { Marker, Polygon, Popup, Tooltip } from 'react-leaflet'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import { cameraStatus } from '../../hooks/useCameraMap.js'
import { viewCone } from '../../lib/geo.js'
import { formatAlertType, formatTimestamp } from '../../lib/utils.js'

const STATUS_COLOR = { alerting: '#ef4444', live: '#10b981', offline: '#71717a', draft: '#f59e0b' }
const THUMBNAIL_MS = 1000

// Leaflet markers take HTML; a small camera glyph in a coloured disc. One icon per
// status, so a refresh does not make Leaflet replace every marker's element.
const ICONS = {}
function cameraIcon(status) {
  ICONS[status] ??= L.divIcon({
    className: `camera-marker camera-marker--${status}`,
    html: `<span style="background:${STATUS_COLOR[status]}"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#0b0d12" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m16 13 5.2 3.5a.5.5 0 0 0 .8-.4V7.9a.5.5 0 0 0-.8-.4L16 11"/><rect x="2" y="6" width="14" height="12" rx="2"/></svg></span>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
    popupAnchor: [0, -12],
  })
  return ICONS[status]
}

/** The camera's latest live frame, refreshed every second while the popup is open. */
function LiveThumbnail({ cameraId, onFirstFrame }) {
  const { api } = useAuth()
  const [url, setUrl] = useState(null)
  const [missing, setMissing] = useState(false)

  useEffect(() => {
    let current = null
    let stopped = false
    async function fetchFrame() {
      try {
        const { data } = await api.get('v1/camera-frames/latest/', { params: { camera_id: cameraId }, responseType: 'blob' })
        if (stopped) return
        const next = URL.createObjectURL(data)
        if (current) URL.revokeObjectURL(current)
        current = next
        setUrl(next)
        setMissing(false)
      } catch {
        if (!stopped) setMissing(true)
      }
    }
    void fetchFrame()
    const timer = window.setInterval(fetchFrame, THUMBNAIL_MS)
    return () => {
      stopped = true
      window.clearInterval(timer)
      if (current) URL.revokeObjectURL(current)
    }
  }, [api, cameraId])

  if (missing && !url) return <p className="text-[11px] text-zinc-500">No live picture right now.</p>
  return url ? (
    <img
      src={url}
      alt={`Live view from ${cameraId}`}
      onLoad={onFirstFrame}
      className="mb-1.5 aspect-video w-60 rounded bg-black object-contain"
    />
  ) : (
    <div className="mb-1.5 aspect-video w-60 rounded bg-black" />
  )
}

function CameraPopup({ camera, status, canViewLive, relayout }) {
  const last = camera.last_alert
  // Leaflet sizes and pans the popup before React fills it in; measure again once it has content.
  useEffect(() => relayout(), [relayout])
  return (
    <div className="space-y-1 text-xs text-zinc-200">
      <p className="flex items-center justify-between gap-3">
        <span>
          <span className="font-mono font-semibold text-zinc-100">{camera.camera_id}</span>
          <span className="ml-1.5 text-zinc-400">{camera.zone || 'No zone'}</span>
        </span>
        <span style={{ color: STATUS_COLOR[status] }} className="font-semibold">
          {status === 'alerting' ? 'Alert' : camera.live ? 'Live' : 'Offline'}
        </span>
      </p>
      {canViewLive && camera.live ? <LiveThumbnail cameraId={camera.camera_id} onFirstFrame={relayout} /> : null}
      <p>
        People in view:{' '}
        <span className="font-semibold">{camera.people_in_view ?? '—'}</span>
        {camera.people_in_view == null ? <span className="text-zinc-500"> (no recent count)</span> : null}
      </p>
      <p>
        Open alerts: <span className="font-semibold">{camera.open_alerts}</span>
        {last ? (
          <span className="text-zinc-400">
            {' '}
            · last {formatAlertType(last.alert_type).toLowerCase()} {formatTimestamp(last.timestamp).split(' · ')[0]}
          </span>
        ) : null}
      </p>
      {!camera.live && camera.last_frame_at ? (
        <p className="text-zinc-500">Last picture {formatTimestamp(camera.last_frame_at)}</p>
      ) : null}
      {canViewLive ? (
        <Link to={`/cameras?camera=${encodeURIComponent(camera.camera_id)}`} className="inline-block pt-0.5 text-amber-400 hover:text-amber-300">
          Open live view →
        </Link>
      ) : null}
    </div>
  )
}

function CameraMarker({ camera, status, canViewLive }) {
  const popup = useRef(null)
  // update() re-measures the popup and pans the map so it is fully in view.
  const relayout = useCallback(() => popup.current?.update(), [])
  return (
    <Marker
      position={[camera.placement.latitude, camera.placement.longitude]}
      icon={cameraIcon(status)}
      zIndexOffset={status === 'alerting' ? 1000 : 0}
    >
      <Tooltip direction="top" offset={[0, -12]}>
        {camera.camera_id}
        {camera.people_in_view != null ? ` · ${camera.people_in_view} in view` : ''}
      </Tooltip>
      <Popup ref={popup} minWidth={250} autoPanPaddingTopLeft={[56, 12]}>
        <CameraPopup camera={camera} status={status} canViewLive={canViewLive} relayout={relayout} />
      </Popup>
    </Marker>
  )
}

/**
 * Placed cameras on the site map (FR-33): each draws its view cone and a
 * marker, green while its live view is current, grey when offline and red
 * for a minute after it raises an alert. ``draft`` is a placement being
 * edited, drawn in amber.
 */
export default function CameraLayer({ cameras = [], alerting = {}, draft = null }) {
  const { canOperate } = useAuth()
  const placed = cameras.filter((c) => c.placement && c.camera_id !== draft?.camera_id)

  return (
    <>
      {placed.map((camera) => {
        const status = cameraStatus(camera, alerting)
        const p = camera.placement
        return (
          <Polygon
            key={`cone-${camera.camera_id}`}
            positions={viewCone(p)}
            pathOptions={{
              color: STATUS_COLOR[status],
              weight: 1,
              fillOpacity: status === 'alerting' ? 0.3 : 0.15,
              dashArray: camera.live ? undefined : '4 4',
            }}
            interactive={false}
          />
        )
      })}
      {placed.map((camera) => (
        <CameraMarker
          key={`cam-${camera.camera_id}`}
          camera={camera}
          status={cameraStatus(camera, alerting)}
          canViewLive={canOperate}
        />
      ))}
      {draft?.latitude != null ? (
        <>
          <Polygon positions={viewCone(draft)} pathOptions={{ color: STATUS_COLOR.draft, weight: 2, fillOpacity: 0.25 }} interactive={false} />
          <Marker position={[draft.latitude, draft.longitude]} icon={cameraIcon('draft')} interactive={false} />
        </>
      ) : null}
    </>
  )
}
