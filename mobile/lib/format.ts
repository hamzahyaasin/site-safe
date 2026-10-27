import type { Severity, Worker } from './types';

export function formatType(type: string): string {
  const words = type.toLowerCase().split('_');
  const acronyms: Record<string, string> = { ppe: 'PPE', sos: 'SOS' };
  const text = words.map((w) => acronyms[w] ?? w).join(' ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function timeAgo(iso: string | null, now = Date.now()): string {
  if (!iso) return 'never';
  const mins = Math.floor((now - new Date(iso).getTime()) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  if (mins < 1440) return `${Math.floor(mins / 60)} h ago`;
  return `${Math.floor(mins / 1440)} d ago`;
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export const SEVERITY_COLOR: Record<Severity, string> = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  MEDIUM: '#eab308',
  LOW: '#3b82f6',
};

export type Presence = { label: string; tone: 'good' | 'bad' | 'muted' | 'alert' };

/** Same rules as the dashboard: presence from vest telemetry and camera badge sightings. */
export function workerPresence(worker: Worker): Presence {
  if (!worker.is_active) return { label: 'Inactive', tone: 'muted' };
  const vest = worker.smart_vest;
  if (vest?.sos_active) return { label: 'SOS', tone: 'alert' };
  // A vest counts as online only once it has reported.
  if (worker.location?.current || (vest?.is_online && vest.last_seen)) return { label: 'On site', tone: 'good' };
  if (worker.last_seen_at || vest?.last_seen) return { label: 'Not in view', tone: 'bad' };
  if (vest) return { label: 'Never reported', tone: 'muted' };
  return { label: 'Not seen yet', tone: 'muted' };
}

/** "In Bay 1 · CAM-02", "Last seen in Bay 1 · CAM-02 · 4 min ago", or null if never placed. */
export function describeLocation(worker: Worker, now = Date.now()): string | null {
  const loc = worker.location;
  if (!loc) return null;
  const device = loc.source === 'vest' ? `vest ${loc.device}` : loc.device;
  const where = loc.zone_name ? `in ${loc.zone_name}` : loc.source === 'vest' ? 'outside all zones' : 'in view (camera has no zone)';
  if (loc.current) return `${where.charAt(0).toUpperCase()}${where.slice(1)} · ${device}`;
  return `Last seen ${where} · ${device} · ${timeAgo(loc.at, now)}`;
}

export function canOperate(role: string | null | undefined): boolean {
  return role === 'ADMIN' || role === 'SAFETY_OFFICER';
}
