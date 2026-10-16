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
  is_resolved: boolean;
  timestamp: string;
  resolved_at: string | null;
}

export interface SmartVest {
  id: number;
  vest_id: string;
  battery_level: number | null;
  latitude: number | null;
  longitude: number | null;
  sos_active: boolean;
  is_online: boolean;
  last_seen: string | null;
}

export interface Worker {
  id: number;
  name: string;
  role: string;
  vest_id: string | null;
  zone_name: string | null;
  smart_vest: SmartVest | null;
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
