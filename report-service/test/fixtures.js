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
// A 64x48 camera snapshot (JPEG), as served by /api/alerts/<id>/snapshot/.
const JPEG = Buffer.from(
  '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAoHBwgHBgoICAgLCgoLDhgQDg0NDh0VFhEYIx8lJCIfIiEmKzcvJik0KSEiMEExNDk7Pj4+JS5ESUM8SDc9Pjv/2wBDAQoLCw4NDhwQEBw7KCIoOzs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozv/wAARCAAwAEADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDhKKK9XqMwzD6ny+7e9+ttreT7k4XC+3vrax5RRXq9FeZ/b/8A07/H/gHZ/Zn9/wDD/gnlFFer15nq3/IYvf8Ar4k/9CNejgMy+uSceW1vO/6I5MThPYJO97lSiiivVOIK9XryivV6+Zz/AP5d/P8AQ9jLPt/L9Qooor5k9cK8z1b/AJDF7/18Sf8AoRr0yvM9W/5DF7/18Sf+hGvoch/iT9Dy8y+CJUooor6s8QK9Xryirf8Aa2pf9BC6/wC/zf415WZYCWM5eV2tf8bf5HbhMSqF7q9z0yivM/7W1L/oIXX/AH+b/Gj+1tS/6CF1/wB/m/xryf7Bqfzo7v7Sh/KemV5nq3/IYvf+viT/ANCNH9ral/0ELr/v83+NVXdpHZ3YszHLMTkk+tenl2XTwk5SlK9zjxWKjXiklawlFFFewcB//9k=',
  'base64',
)
module.exports = { zones, workers, alerts, dailyActivity, JPEG }
