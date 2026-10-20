// Fixed fixture: known counts so every figure in a report can be checked.
const zones = [
  { id: 1, name: 'Main Site', risk_level: 'MEDIUM', camera_ids: ['CAM-01'] },
  { id: 2, name: 'Crane Pit', risk_level: 'RESTRICTED', camera_ids: [] },
]
const workers = [
  { id: 10, name: 'Ali Raza', zone: 2, zone_name: 'Crane Pit', is_active: true },
  { id: 11, name: 'Sara Khan', zone: null, zone_name: null, is_active: true },
  { id: 12, name: 'Gone', zone: 1, zone_name: 'Main Site', is_active: false },
]
const t = (iso) => new Date(iso).toISOString()
const alerts = [
  // Camera PPE in Main Site on 2026-10-14 (PKT), identified, resolved after 30 min.
  { id: 1, alert_type: 'PPE_VIOLATION', severity: 'HIGH', source: 'AI_CAMERA', camera_id: 'CAM-01', zone_name: 'Main Site', worker: 10, worker_name: 'Ali Raza', is_resolved: true, timestamp: t('2026-10-14T05:00:00Z'), resolved_at: t('2026-10-14T05:30:00Z'), description: 'Missing PPE: no-helmet' },
  // Camera PPE in Main Site, unidentified, open; 19:30Z on 14th is 00:30 on 15th in PKT.
  { id: 2, alert_type: 'PPE_VIOLATION', severity: 'HIGH', source: 'AI_CAMERA', camera_id: 'CAM-01', zone_name: 'Main Site', worker: null, worker_name: null, is_resolved: false, timestamp: t('2026-10-14T19:30:00Z'), resolved_at: null },
  // Vest SOS, no camera: attributed via Ali's assigned zone (Crane Pit), resolved after 90 min.
  { id: 3, alert_type: 'SOS', severity: 'CRITICAL', source: 'SMART_VEST', camera_id: '', zone_name: null, worker: 10, worker_name: 'Ali Raza', is_resolved: true, timestamp: t('2026-10-15T08:00:00Z'), resolved_at: t('2026-10-15T09:30:00Z') },
  // Fall for Sara who has no zone: Unattributed.
  { id: 4, alert_type: 'FALL', severity: 'CRITICAL', source: 'AI_CAMERA', camera_id: 'CAM-09', zone_name: null, worker: 11, worker_name: 'Sara Khan', is_resolved: false, timestamp: t('2026-10-15T10:00:00Z'), resolved_at: null },
  // Vest breach inside Crane Pit by Sara (no assigned zone): the API's zone_name wins.
  { id: 6, alert_type: 'ZONE_BREACH', severity: 'HIGH', source: 'SMART_VEST', camera_id: '', zone_name: 'Crane Pit', worker: 11, worker_name: 'Sara Khan', is_resolved: false, timestamp: t('2026-10-16T04:00:00Z'), resolved_at: null },
  // Simulated: excluded from figures.
  { id: 5, alert_type: 'PPE_VIOLATION', severity: 'HIGH', source: 'SIMULATED', camera_id: '', zone_name: null, worker: 11, worker_name: 'Sara Khan', is_resolved: false, timestamp: t('2026-10-15T11:00:00Z'), resolved_at: null },
]
// As returned by /api/v1/activity/daily/ (times in UTC; tz Asia/Karachi is +5).
const dailyActivity = [
  { worker: 10, worker_name: 'Ali Raza', date: '2026-10-14', first_check_in: t('2026-10-14T03:00:00Z'), last_check_out: t('2026-10-14T11:00:00Z'), on_site_minutes: 480, idle_minutes: 30, zone_minutes: {}, sessions: 1, still_open: false },
  { worker: 10, worker_name: 'Ali Raza', date: '2026-10-15', first_check_in: t('2026-10-15T04:00:00Z'), last_check_out: t('2026-10-15T10:00:00Z'), on_site_minutes: 360, idle_minutes: 60, zone_minutes: {}, sessions: 1, still_open: false },
  { worker: 11, worker_name: 'Sara Khan', date: '2026-10-15', first_check_in: t('2026-10-15T06:00:00Z'), last_check_out: null, on_site_minutes: 120, idle_minutes: 0, zone_minutes: {}, sessions: 1, still_open: true },
]
module.exports = { zones, workers, alerts, dailyActivity }
