export type Role = 'ADMIN' | 'SAFETY_OFFICER' | 'VIEWER';

export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface Alert {
  id: number;
  worker: number | null;
  worker_name: string | null;
  vest_id: string | null;
  alert_type: string;
  severity: Severity;
  source: 'AI_CAMERA' | 'SMART_VEST' | 'SIMULATED';
  description: string;
  camera_id: string;
  zone_name: string | null;
  location: { lat: number; lng: number } | null;
  confidence: number | null;
  /** Weights that raised an AI alert: file name and SHA-256 prefix (FR-29). */
  model_version: string;
  /** API path of the evidence frame, or null; fetch with api.imageDataUri. */
  snapshot: string | null;
  is_resolved: boolean;
  timestamp: string;
  resolved_at: string | null;
}

export interface SmartVest {
  id: number;
  vest_id: string;
  worker_name?: string | null;
  battery_level: number | null;
  latitude: number | null;
  longitude: number | null;
  sos_active: boolean;
  /** Last gas reading (ppm), null if the vest has not sent one. */
  gas_ppm?: number | null;
  gas_over_limit?: boolean;
  is_online: boolean;
  last_seen: string | null;
}

/** Where a camera badge sighting or vest GPS last placed the worker. */
export interface WorkerLocation {
  zone: number | null;
  zone_name: string | null;
  source: 'camera' | 'vest';
  device: string;
  at: string;
  current: boolean;
}

export interface Worker {
  id: number;
  name: string;
  role: string;
  vest_id: string | null;
  zone_name: string | null;
  smart_vest: SmartVest | null;
  location: WorkerLocation | null;
  last_seen_at: string | null;
  is_active: boolean;
}

export interface Zone {
  id: number;
  name: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'RESTRICTED';
  boundaries: { lat: number; lng: number }[];
  camera_ids: string[];
  max_occupancy: number;
  is_active: boolean;
  /** Head count now (identified workers and camera people counts). */
  current_occupancy?: number;
}

/** Where a camera is on the site map and what it covers (FR-33). */
export interface CameraPlacement {
  latitude: number;
  longitude: number;
  /** Degrees clockwise from north. */
  heading: number;
  field_of_view: number;
  view_range_m: number;
}

/** One camera from /api/v1/camera-map/. */
export interface MapCamera {
  camera_id: string;
  zone: string | null;
  live: boolean;
  last_frame_at: string | null;
  /** People in view now, or null when the camera has no recent count. */
  people_in_view: number | null;
  placement: CameraPlacement | null;
  open_alerts: number;
  last_alert: { id: number; alert_type: string; severity: Severity; timestamp: string; is_resolved: boolean } | null;
}

/** A danger area drawn on a camera's picture (FR-32); corners are fractions of the picture. */
export interface CameraArea {
  id: number;
  camera_id: string;
  name: string;
  polygon: [number, number][];
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  is_active: boolean;
}

export interface Profile {
  email: string;
  full_name: string;
  role: Role;
  role_label: string;
  notify_push: boolean;
  notify_email: boolean;
}
