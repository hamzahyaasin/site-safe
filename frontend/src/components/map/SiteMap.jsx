import { useEffect, useRef } from 'react'
import { CircleMarker, MapContainer, Polygon, Polyline, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { formatTimestamp } from '../../lib/utils.js'

const RISK_COLOR = {
  LOW: '#3b82f6',
  MEDIUM: '#eab308',
  HIGH: '#f97316',
  RESTRICTED: '#ef4444',
}

// Fallback view before any zone or vest position exists; override per site.
const DEFAULT_CENTER = (import.meta.env.VITE_MAP_CENTER || '33.6844,73.0479').split(',').map(Number)
const DEFAULT_ZOOM = 16

function toLatLng(point) {
  return Array.isArray(point) ? point : [point.lat, point.lng]
}

/** Fit the view to the site whenever the set of zones changes (first load,
 * zone added or removed). Vest movement never re-fits, so the operator's
 * pan/zoom is kept while positions update. */
function FitToSite({ zonePoints, otherPoints, zoneKey }) {
  const map = useMap()
  const fittedKey = useRef(null)
  useEffect(() => {
    if (fittedKey.current === zoneKey) return
    const points = zonePoints.length ? zonePoints : otherPoints
    if (points.length === 0) return
    fittedKey.current = zoneKey
    if (points.length === 1) map.setView(points[0], 18)
    else map.fitBounds(points, { padding: [24, 24], maxZoom: 19 })
  }, [map, zonePoints, otherPoints, zoneKey])
  return null
}

function ClickToAdd({ onAddPoint }) {
  useMapEvents({
    click(e) {
      onAddPoint?.({ lat: Number(e.latlng.lat.toFixed(7)), lng: Number(e.latlng.lng.toFixed(7)) })
    },
  })
  return null
}

/**
 * Site map: zone polygons coloured by risk and vest positions as last
 * reported. Offline vests are grey and show the age of their last report,
 * so a stale position is never presented as live.
 *
 * Pass ``draft``/``onAddPoint`` to use it as a boundary editor: each map
 * click appends a vertex to the draft polygon.
 */
export default function SiteMap({
  zones = [],
  vests = [],
  draft,
  onAddPoint,
  excludeZoneId,
  height = 420,
}) {
  const shownZones = zones.filter((z) => z.id !== excludeZoneId && z.boundaries?.length >= 3)
  const located = vests.filter((v) => v.latitude !== null && v.longitude !== null)
  const zonePoints = shownZones.flatMap((z) => z.boundaries.map(toLatLng))
  const otherPoints = located.map((v) => [v.latitude, v.longitude])
  const zoneKey = shownZones.map((z) => z.id).join(',') || 'none'

  const draftLatLngs = (draft ?? []).map(toLatLng)

  return (
    <div className="relative isolate z-0 overflow-hidden rounded-lg border border-zinc-800" style={{ height }}>
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        maxZoom={20}
        scrollWheelZoom
        className="h-full w-full"
        style={{ background: '#0f1117', cursor: onAddPoint ? 'crosshair' : undefined }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxNativeZoom={19}
          maxZoom={20}
        />
        <FitToSite zonePoints={zonePoints} otherPoints={otherPoints} zoneKey={zoneKey} />
        {onAddPoint ? <ClickToAdd onAddPoint={onAddPoint} /> : null}

        {shownZones.map((zone) => (
          <Polygon
            key={zone.id}
            positions={zone.boundaries.map(toLatLng)}
            pathOptions={{
              color: RISK_COLOR[zone.risk_level] || '#a1a1aa',
              weight: 2,
              fillOpacity: draft ? 0.05 : 0.15,
              dashArray: zone.is_active ? undefined : '6 6',
            }}
          >
            <Tooltip sticky>
              {zone.name} · {zone.risk_level}
              {zone.current_occupancy !== undefined ? ` · ${zone.current_occupancy} present` : ''}
              {zone.max_occupancy ? ` / ${zone.max_occupancy}` : ''}
              {zone.is_active ? '' : ' · inactive'}
            </Tooltip>
          </Polygon>
        ))}

        {draftLatLngs.length >= 3 ? (
          <Polygon positions={draftLatLngs} pathOptions={{ color: '#f59e0b', weight: 2, fillOpacity: 0.2 }} />
        ) : draftLatLngs.length === 2 ? (
          <Polyline positions={draftLatLngs} pathOptions={{ color: '#f59e0b', weight: 2 }} />
        ) : null}
        {draftLatLngs.map((p, i) => (
          <CircleMarker key={`d-${i}`} center={p} radius={4} pathOptions={{ color: '#f59e0b', fillOpacity: 1 }} />
        ))}

        {located.map((vest) => (
          <CircleMarker
            key={vest.id}
            center={[vest.latitude, vest.longitude]}
            radius={vest.sos_active ? 9 : 7}
            pathOptions={{
              color: vest.sos_active ? '#ef4444' : vest.is_online ? '#22c55e' : '#71717a',
              fillOpacity: 0.85,
              weight: 2,
            }}
          >
            <Tooltip>
              {vest.worker_name || 'Unassigned'} ({vest.vest_id})
              {vest.sos_active ? ' · SOS' : vest.is_online ? ' · online' : ' · offline'}
              <br />
              Last report {formatTimestamp(vest.last_seen)}
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  )
}

