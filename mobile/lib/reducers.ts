import type { LiveEvent } from '@/context/Live';
import type { Alert, GasMonitor, SmartVest, Worker, Zone } from './types';

/** Apply one live event to an alert list. ``onlyOpen`` lists drop resolved alerts. */
export function reduceAlerts(onlyOpen: boolean) {
  return (list: Alert[], event: LiveEvent, alert: Alert): Alert[] => {
    if (event === 'alert_created') {
      if (onlyOpen && alert.is_resolved) return list;
      return list.some((a) => a.id === alert.id) ? list : [alert, ...list];
    }
    if (event === 'alert_updated' || event === 'alert_resolved') {
      if (onlyOpen && alert.is_resolved) return list.filter((a) => a.id !== alert.id);
      return list.map((a) => (a.id === alert.id ? alert : a));
    }
    return list;
  };
}

/** Apply a worker_status_update to a worker list (unknown workers are ignored until reload). */
export function reduceWorkers(list: Worker[], event: LiveEvent, worker: Worker): Worker[] {
  if (event !== 'worker_status_update') return list;
  return list.map((w) => (w.id === worker.id ? worker : w));
}

/** Apply a zone_updated (head count, boundary or settings changed) to a zone list. */
export function reduceZones(list: Zone[], event: LiveEvent, zone: Zone): Zone[] {
  if (event !== 'zone_updated' || !zone?.id) return list;
  return list.map((z) => (z.id === zone.id ? zone : z));
}

/** Apply a vest_updated (position, battery, SOS, online) to a vest list. */
export function reduceVests(list: SmartVest[], event: LiveEvent, vest: SmartVest): SmartVest[] {
  if (event !== 'vest_updated' || !vest?.id) return list;
  return list.some((v) => v.id === vest.id) ? list.map((v) => (v.id === vest.id ? vest : v)) : [vest, ...list];
}

/** Apply gas_monitor_updated / gas_monitor_deleted to a gas monitor list. */
export function reduceGasMonitors(list: GasMonitor[], event: LiveEvent, monitor: GasMonitor): GasMonitor[] {
  if (!monitor?.id) return list;
  if (event === 'gas_monitor_deleted') return list.filter((m) => m.id !== monitor.id);
  if (event !== 'gas_monitor_updated') return list;
  return list.some((m) => m.id === monitor.id) ? list.map((m) => (m.id === monitor.id ? monitor : m)) : [...list, monitor];
}
