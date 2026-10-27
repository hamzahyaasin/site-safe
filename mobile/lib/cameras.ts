import type { LiveEvent } from '@/context/Live';
import type { CameraPlacement, MapCamera } from './types';

// How long a camera shows as alerting after it raises an alert, as on the web map.
export const ALERT_FLASH_MS = 60000;

export type CameraStatus = 'alerting' | 'live' | 'offline';

export const STATUS_COLOR: Record<CameraStatus, string> = {
  alerting: '#ef4444',
  live: '#10b981',
  offline: '#71717a',
};

export const STATUS_LABEL: Record<CameraStatus, string> = { alerting: 'Alert', live: 'Live', offline: 'Offline' };

/** camera_id -> when its latest alert arrived over the live socket. */
export type Alerting = Record<string, number>;

export function cameraStatus(camera: MapCamera, alerting: Alerting, now = Date.now()): CameraStatus {
  const at = alerting[camera.camera_id];
  if (at !== undefined && now - at < ALERT_FLASH_MS) return 'alerting';
  return camera.live ? 'live' : 'offline';
}

/** Apply a camera_updated event (placement or people count changed) to the camera list. */
export function reduceCameras(list: MapCamera[], event: LiveEvent, camera: MapCamera): MapCamera[] {
  if (event !== 'camera_updated' || !camera?.camera_id) return list;
  if (list.some((c) => c.camera_id === camera.camera_id)) {
    return list.map((c) => (c.camera_id === camera.camera_id ? camera : c));
  }
  return [...list, camera].sort((a, b) => a.camera_id.localeCompare(b.camera_id));
}

const METRES_PER_DEGREE = 111320;

/** The point ``metres`` from [lat, lng] in compass direction ``bearing``. */
export function offset([lat, lng]: [number, number], bearing: number, metres: number): [number, number] {
  const rad = (bearing * Math.PI) / 180;
  return [
    lat + (metres * Math.cos(rad)) / METRES_PER_DEGREE,
    lng + (metres * Math.sin(rad)) / (METRES_PER_DEGREE * Math.cos((lat * Math.PI) / 180)),
  ];
}

/** A camera's view cone: its position, then an arc ``view_range_m`` away across its view angle. */
export function viewCone(p: CameraPlacement, steps = 16): [number, number][] {
  const origin: [number, number] = [p.latitude, p.longitude];
  const arc = Array.from({ length: steps + 1 }, (_, i) =>
    offset(origin, p.heading - p.field_of_view / 2 + (p.field_of_view * i) / steps, p.view_range_m),
  );
  return [origin, ...arc];
}

/** A danger area's corners (fractions of the picture) as SVG points on a ``width`` x ``height`` view. */
export function areaPoints(polygon: [number, number][], width: number, height: number): string {
  return polygon.map(([x, y]) => `${(x * width).toFixed(1)},${(y * height).toFixed(1)}`).join(' ');
}
