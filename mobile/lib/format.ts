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

/** Same rules as the dashboard: presence comes only from vest telemetry. */
export function workerPresence(worker: Worker): Presence {
  if (!worker.is_active) return { label: 'Inactive', tone: 'muted' };
  const vest = worker.smart_vest;
  if (!vest) return { label: 'No vest', tone: 'muted' };
  if (!vest.last_seen) return { label: 'Never reported', tone: 'muted' };
  if (vest.sos_active) return { label: 'SOS', tone: 'alert' };
  return vest.is_online ? { label: 'On site', tone: 'good' } : { label: 'Offline', tone: 'bad' };
}

export function canOperate(role: string | null | undefined): boolean {
  return role === 'ADMIN' || role === 'SAFETY_OFFICER';
}
