import { ALERT_FLASH_MS, areaPoints, cameraStatus, offset, reduceCameras, viewCone } from '@/lib/cameras';
import { reduceVests, reduceZones } from '@/lib/reducers';
import { parseMapMessage, siteMapData, siteMapHtml } from '@/lib/siteMap';
import type { MapCamera, SmartVest, Zone } from '@/lib/types';

const PLACE = { latitude: 33.6851, longitude: 73.0482, heading: 90, field_of_view: 60, view_range_m: 40 };
const camera = (id: string, over: Partial<MapCamera> = {}): MapCamera => ({
  camera_id: id,
  zone: 'Bay 1',
  live: true,
  last_frame_at: null,
  people_in_view: 2,
  placement: PLACE,
  open_alerts: 0,
  last_alert: null,
  ...over,
});

test('a camera is alerting for a minute after its alert, else live or offline', () => {
  const now = 1_000_000;
  expect(cameraStatus(camera('CAM-01'), {}, now)).toBe('live');
  expect(cameraStatus(camera('CAM-01', { live: false }), {}, now)).toBe('offline');
  expect(cameraStatus(camera('CAM-01', { live: false }), { 'CAM-01': now - 1000 }, now)).toBe('alerting');
  expect(cameraStatus(camera('CAM-01'), { 'CAM-01': now - ALERT_FLASH_MS }, now)).toBe('live');
});

test('camera_updated replaces or adds a camera, in id order', () => {
  let list = [camera('CAM-02')];
  list = reduceCameras(list, 'camera_updated', camera('CAM-01'));
  list = reduceCameras(list, 'camera_updated', camera('CAM-02', { people_in_view: 5 }));
  expect(list.map((c) => [c.camera_id, c.people_in_view])).toEqual([
    ['CAM-01', 2],
    ['CAM-02', 5],
  ]);
  expect(reduceCameras(list, 'alert_created', camera('CAM-03'))).toBe(list);
});

test('the view cone starts at the camera and reaches its range across its view angle', () => {
  const cone = viewCone(PLACE, 4);
  expect(cone).toHaveLength(6);
  expect(cone[0]).toEqual([PLACE.latitude, PLACE.longitude]);
  // Facing east, the middle of the arc is 40 m due east: same latitude, larger longitude.
  const [lat, lng] = cone[3];
  expect(lat).toBeCloseTo(PLACE.latitude, 6);
  expect(lng).toBeGreaterThan(PLACE.longitude);
  const metresEast = (lng - PLACE.longitude) * 111320 * Math.cos((PLACE.latitude * Math.PI) / 180);
  expect(metresEast).toBeCloseTo(40, 1);
  expect(offset([0, 0], 0, 111320)).toEqual([1, 0]);
});

test('danger area corners scale from picture fractions to the shown size', () => {
  expect(
    areaPoints(
      [
        [0.5, 0.5],
        [1, 0],
        [0, 1],
      ],
      200,
      100,
    ),
  ).toBe('100.0,50.0 200.0,0.0 0.0,100.0');
});

test('zone and vest updates apply to their lists', () => {
  const zone = { id: 1, name: 'Bay 1', current_occupancy: 1 } as Zone;
  expect(reduceZones([zone], 'zone_updated', { ...zone, current_occupancy: 3 })[0].current_occupancy).toBe(3);
  const vest = { id: 4, vest_id: 'V1' } as SmartVest;
  expect(reduceVests([], 'vest_updated', vest)).toEqual([vest]);
});

test('site map data: zones with head counts, located vests, placed cameras with cones', () => {
  const zones = [
    {
      id: 1,
      name: 'Bay 1',
      risk_level: 'MEDIUM',
      boundaries: [
        { lat: 0, lng: 0 },
        { lat: 0, lng: 1 },
        { lat: 1, lng: 1 },
      ],
      camera_ids: [],
      max_occupancy: 3,
      is_active: true,
      current_occupancy: 2,
    },
    { id: 2, name: 'Camera only', risk_level: 'LOW', boundaries: [], camera_ids: [], max_occupancy: 0, is_active: true },
  ] as Zone[];
  const vests = [
    { id: 1, vest_id: 'V1', worker_name: 'Ali', latitude: 1, longitude: 2, sos_active: true, is_online: true },
    { id: 2, vest_id: 'V2', latitude: null, longitude: null, sos_active: false, is_online: false },
  ] as SmartVest[];
  const cams = [camera('CAM-01'), camera('CAM-02', { placement: null })];
  const data = siteMapData(zones, vests, cams, { 'CAM-01': 999 }, 1000);
  expect(data.zones.map((z) => [z.label, z.color])).toEqual([['Bay 1: 2 / 3 present', '#eab308']]);
  expect(data.vests.map((v) => [v.label, v.color])).toEqual([['Ali (V1) · SOS', '#ef4444']]);
  expect(data.cameras.map((c) => [c.id, c.color, c.label])).toEqual([['CAM-01', '#ef4444', 'CAM-01 · 2 in view']]);
  expect(data.cameras[0].cone.length).toBeGreaterThan(3);
});

test('the map page pins Leaflet by integrity hash and escapes names it shows', () => {
  const html = siteMapHtml([33.68, 73.04]);
  expect(html).toContain('leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="');
  expect(html).toContain('bindTooltip(esc(z.label)');
  expect(html).toContain("post({ type: 'camera', id: c.id })");
});

test('only well-formed map messages are acted on', () => {
  expect(parseMapMessage('{"type":"camera","id":"CAM-01"}')).toEqual({ type: 'camera', id: 'CAM-01' });
  expect(parseMapMessage('{"type":"ready"}')).toEqual({ type: 'ready' });
  expect(parseMapMessage('{"type":"camera","id":7}')).toBeNull();
  expect(parseMapMessage('{"type":"navigate","url":"x"}')).toBeNull();
  expect(parseMapMessage('not json')).toBeNull();
  expect(parseMapMessage({ type: 'ready' })).toBeNull();
});
