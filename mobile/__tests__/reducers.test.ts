import { canOperate, describeLocation, formatType, workerPresence } from '@/lib/format';
import { reduceAlerts, reduceWorkers } from '@/lib/reducers';
import type { Alert, Worker } from '@/lib/types';

const alert = (id: number, over: Partial<Alert> = {}): Alert =>
  ({ id, alert_type: 'FALL', severity: 'HIGH', is_resolved: false, ...over }) as Alert;

test('open list adds new alerts once and drops resolved ones', () => {
  const open = reduceAlerts(true);
  let list = open([], 'alert_created', alert(1));
  list = open(list, 'alert_created', alert(1));
  list = open(list, 'alert_created', alert(2));
  expect(list.map((a) => a.id)).toEqual([2, 1]);
  list = open(list, 'alert_resolved', alert(1, { is_resolved: true }));
  expect(list.map((a) => a.id)).toEqual([2]);
});

test('full list keeps resolved alerts, updated in place', () => {
  const all = reduceAlerts(false);
  const list = all([alert(1)], 'alert_resolved', alert(1, { is_resolved: true }));
  expect(list).toHaveLength(1);
  expect(list[0].is_resolved).toBe(true);
});

test('worker updates replace the matching worker only', () => {
  const w = (id: number, name: string) => ({ id, name }) as Worker;
  const list = reduceWorkers([w(1, 'A'), w(2, 'B')], 'worker_status_update', w(2, 'B2'));
  expect(list.map((x) => x.name)).toEqual(['A', 'B2']);
  expect(reduceWorkers(list, 'alert_created', w(1, 'X'))).toBe(list);
});

test('presence comes from vest telemetry only', () => {
  const base = { id: 1, name: 'A', role: '', vest_id: null, zone_name: null, is_active: true } as Worker;
  const vest = { id: 9, vest_id: 'V', battery_level: null, latitude: null, longitude: null, sos_active: false, is_online: true, last_seen: '2026-10-16T10:00:00Z' };
  expect(workerPresence({ ...base, smart_vest: null }).label).toBe('Not seen yet');
  expect(workerPresence({ ...base, smart_vest: { ...vest, last_seen: null } }).label).toBe('Never reported');
  expect(workerPresence({ ...base, smart_vest: vest }).label).toBe('On site');
  expect(workerPresence({ ...base, smart_vest: { ...vest, is_online: false } }).label).toBe('Not in view');
  expect(workerPresence({ ...base, smart_vest: { ...vest, sos_active: true } }).label).toBe('SOS');
  expect(workerPresence({ ...base, is_active: false, smart_vest: vest }).label).toBe('Inactive');
});

test('labels and roles', () => {
  expect(formatType('PPE_VIOLATION')).toBe('PPE violation');
  expect(canOperate('VIEWER')).toBe(false);
  expect(canOperate('SAFETY_OFFICER')).toBe(true);
});

test('camera sightings place workers without a vest', () => {
  const now = Date.parse('2026-10-27T10:00:00Z');
  const seen = {
    id: 9,
    name: 'Sara',
    is_active: true,
    smart_vest: null,
    last_seen_at: '2026-10-27T09:59:50Z',
    location: { zone: 1, zone_name: 'Bay 1', source: 'camera', device: 'CAM-02', at: '2026-10-27T09:59:50Z', current: true },
  } as Worker;
  expect(workerPresence(seen).label).toBe('On site');
  expect(describeLocation(seen, now)).toBe('In Bay 1 · CAM-02');
  const gone = { ...seen, location: { ...seen.location!, current: false, at: '2026-10-27T09:56:00Z' } };
  expect(workerPresence(gone).label).toBe('Not in view');
  expect(describeLocation(gone, now)).toBe('Last seen in Bay 1 · CAM-02 · 4 min ago');
  expect(describeLocation({ ...seen, location: null })).toBeNull();
});
