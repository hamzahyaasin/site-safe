import { type Alerting, cameraStatus, STATUS_COLOR, viewCone } from './cameras';
import { formatGas } from './format';
import type { MapCamera, SmartVest, Zone } from './types';

// Same colours as the web site map.
export const RISK_COLOR: Record<Zone['risk_level'], string> = {
  LOW: '#3b82f6',
  MEDIUM: '#eab308',
  HIGH: '#f97316',
  RESTRICTED: '#ef4444',
};

type LatLng = [number, number];

export interface SiteMapData {
  zones: { id: number; color: string; points: LatLng[]; label: string; active: boolean }[];
  vests: { id: number; at: LatLng; color: string; label: string }[];
  cameras: { id: string; at: LatLng; cone: LatLng[]; color: string; live: boolean; label: string }[];
}

/** What the map page draws: zones with head counts, vests, and placed cameras with their cones. */
export function siteMapData(
  zones: Zone[],
  vests: SmartVest[],
  cameras: MapCamera[],
  alerting: Alerting,
  now = Date.now(),
): SiteMapData {
  return {
    zones: zones
      .filter((z) => (z.boundaries?.length ?? 0) >= 3)
      .map((z) => ({
        id: z.id,
        color: RISK_COLOR[z.risk_level] ?? '#a1a1aa',
        points: z.boundaries.map((p) => [p.lat, p.lng] as LatLng),
        label:
          z.current_occupancy === undefined
            ? z.name
            : `${z.name}: ${z.current_occupancy}${z.max_occupancy ? ` / ${z.max_occupancy}` : ''} present`,
        active: z.is_active,
      })),
    vests: vests
      .filter((v) => v.latitude !== null && v.longitude !== null)
      .map((v) => ({
        id: v.id,
        at: [v.latitude as number, v.longitude as number],
        color: v.sos_active || v.gas_over_limit ? '#ef4444' : v.is_online ? '#22c55e' : '#71717a',
        label:
          `${v.worker_name || 'Unassigned'} (${v.vest_id})${v.sos_active ? ' · SOS' : v.is_online ? '' : ' · offline'}` +
          (formatGas(v) ? ` · gas ${formatGas(v)}${v.gas_over_limit ? ' (over limit)' : ''}` : ''),
      })),
    cameras: cameras
      .filter((c) => c.placement)
      .map((c) => {
        const p = c.placement!;
        return {
          id: c.camera_id,
          at: [p.latitude, p.longitude] as LatLng,
          cone: viewCone(p),
          color: STATUS_COLOR[cameraStatus(c, alerting, now)],
          live: c.live,
          label: `${c.camera_id}${c.people_in_view !== null ? ` · ${c.people_in_view} in view` : ''}`,
        };
      }),
  };
}

// Leaflet 1.9.4 with its published integrity hashes, the same library and
// OpenStreetMap tiles as the web dashboard. No map API key is needed.
const LEAFLET_CSS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
const LEAFLET_CSS_SRI = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
const LEAFLET_JS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
const LEAFLET_JS_SRI = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';

// Where the map opens before it fits the site; the web dashboard's default.
export const DEFAULT_CENTER: LatLng = [33.6844, 73.0479];

export type MapMessage = { type: 'ready' } | { type: 'error' } | { type: 'camera'; id: string };

/** A message from the map page, or null if it is not one. */
export function parseMapMessage(raw: unknown): MapMessage | null {
  if (typeof raw !== 'string') return null;
  try {
    const msg = JSON.parse(raw);
    if (msg?.type === 'ready' || msg?.type === 'error') return { type: msg.type };
    if (msg?.type === 'camera' && typeof msg.id === 'string') return { type: 'camera', id: msg.id };
  } catch {
    // not ours
  }
  return null;
}

/**
 * The map page shown in a WebView (or an iframe on the web build). The app calls ``window.render(data)``
 * with ``siteMapData``; the page posts ``{type: 'ready'}`` once Leaflet has
 * loaded, ``{type: 'error'}`` if it could not, and ``{type: 'camera', id}``
 * when a camera is tapped. The view fits the site when the set of zones
 * changes, never on live updates, so the user's pan and zoom are kept.
 */
export function siteMapHtml(center: LatLng): string {
  return `<!doctype html>
<html><head>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<link rel="stylesheet" href="${LEAFLET_CSS}" integrity="${LEAFLET_CSS_SRI}" crossorigin="">
<style>
  html, body, #map { margin: 0; height: 100%; background: #0f1117; }
  .leaflet-tooltip.zone { background: rgba(15,17,23,.85); color: #f4f4f5; border: 1px solid #3f3f46; border-radius: 4px; box-shadow: none; font: 600 11px -apple-system, Roboto, sans-serif; padding: 2px 6px; }
  .leaflet-tooltip.zone::before { display: none; }
  .cam { background: none; border: none; }
  .cam span { display: flex; width: 30px; height: 30px; align-items: center; justify-content: center; border: 2px solid #0b0d12; border-radius: 50%; box-shadow: 0 0 0 1px rgba(255,255,255,.25); }
</style>
</head><body><div id="map"></div>
<script src="${LEAFLET_JS}" integrity="${LEAFLET_JS_SRI}" crossorigin=""></script>
<script>
(function () {
  // A WebView in the app, or an iframe in the app's web build.
  function post(msg) {
    var s = JSON.stringify(msg);
    if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage(s);
    else if (window.parent !== window) window.parent.postMessage(s, '*');
  }
  // Zone and worker names are typed by people; tooltips take HTML.
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return '&#' + c.charCodeAt(0) + ';'; }); }
  if (!window.L) { post({ type: 'error' }); return; }
  var map = L.map('map', { zoomControl: true, attributionControl: true }).setView(${JSON.stringify(center)}, 16);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxNativeZoom: 19, maxZoom: 20, attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);
  var layer = L.layerGroup().addTo(map);
  var fittedKey = null;
  var glyph = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#0b0d12" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 13 5.2 3.5a.5.5 0 0 0 .8-.4V7.9a.5.5 0 0 0-.8-.4L16 11"/><rect x="2" y="6" width="14" height="12" rx="2"/></svg>';
  window.render = function (data) {
    layer.clearLayers();
    data.zones.forEach(function (z) {
      L.polygon(z.points, { color: z.color, weight: 2, fillOpacity: 0.15, dashArray: z.active ? null : '6 6' })
        .bindTooltip(esc(z.label), { permanent: true, direction: 'center', className: 'zone' }).addTo(layer);
    });
    data.cameras.forEach(function (c) {
      L.polygon(c.cone, { color: c.color, weight: 1, fillOpacity: 0.18, dashArray: c.live ? null : '4 4', interactive: false }).addTo(layer);
    });
    data.vests.forEach(function (v) {
      L.circleMarker(v.at, { radius: 7, color: v.color, fillOpacity: 0.85, weight: 2 }).bindTooltip(esc(v.label)).addTo(layer);
    });
    data.cameras.forEach(function (c) {
      var icon = L.divIcon({ className: 'cam', html: '<span style="background:' + c.color + '">' + glyph + '</span>', iconSize: [30, 30], iconAnchor: [15, 15] });
      L.marker(c.at, { icon: icon }).on('click', function () { post({ type: 'camera', id: c.id }); }).addTo(layer);
    });
    var key = data.zones.map(function (z) { return z.id; }).join(',');
    if (key !== fittedKey) {
      var pts = [];
      data.zones.forEach(function (z) { pts = pts.concat(z.points); });
      if (!pts.length) data.cameras.forEach(function (c) { pts.push(c.at); });
      if (!pts.length) data.vests.forEach(function (v) { pts.push(v.at); });
      if (pts.length === 1) map.setView(pts[0], 18);
      else if (pts.length > 1) map.fitBounds(pts, { padding: [24, 24], maxZoom: 19 });
      if (pts.length) fittedKey = key;
    }
  };
  post({ type: 'ready' });
})();
</script>
</body></html>`;
}
