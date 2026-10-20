const test = require('node:test')
const assert = require('node:assert/strict')

const { computeComplianceMetrics, computeIncidentMetrics, dayKey, daysInPeriod } = require('../lib/metrics')
const f = require('./fixtures')

const period = { dateFrom: '2026-10-14', dateTo: '2026-10-16', tz: 'Asia/Karachi' }

test('day keys follow the report time zone', () => {
  assert.equal(dayKey('2026-10-14T19:30:00Z', 'Asia/Karachi'), '2026-10-15')
  assert.equal(dayKey('2026-10-14T19:30:00Z', 'UTC'), '2026-10-14')
  assert.deepEqual(daysInPeriod('2026-10-30', '2026-11-01'), ['2026-10-30', '2026-10-31', '2026-11-01'])
})

test('incident metrics exclude simulated alerts from figures but keep them in the log', () => {
  const m = computeIncidentMetrics({ alerts: f.alerts, tz: 'Asia/Karachi' })
  assert.equal(m.total, 5)
  assert.equal(m.simulated, 1)
  assert.equal(m.open, 3)
  assert.equal(m.resolved, 2)
  assert.equal(m.critical, 2)
  assert.equal(m.identified, 4)
  assert.equal(m.byType.PPE_VIOLATION, 2)
  assert.equal(m.byType.ZONE_BREACH, 1)
  assert.equal(m.byType.FIRE, 0)
  assert.equal(m.underHotWorkPermit, 0)
  assert.equal(m.resolution.medianMinutes, 60) // 30 and 90
  assert.equal(m.log.length, 6)
  assert.equal(m.log[0].id, 6) // newest first
})

test('compliance metrics attribute zones and count violation-free days', () => {
  const m = computeComplianceMetrics({ ...f, ...period })
  assert.equal(m.periodDays, 3)
  assert.equal(m.activeWorkers, 2)
  assert.equal(m.unidentified, 1)
  const zone = Object.fromEntries(m.byZone.map((z) => [z.zone, z]))
  assert.deepEqual(Object.keys(zone), ['Main Site', 'Crane Pit', 'Unattributed'])
  assert.equal(zone['Main Site'].incidents, 2)
  assert.equal(zone['Main Site'].ppeViolations, 2)
  // PPE on 14th and (PKT) 15th -> only the 16th is violation-free.
  assert.equal(zone['Main Site'].daysWithoutPpeViolation, 1)
  assert.equal(zone['Main Site'].medianResolutionMinutes, 30)
  assert.equal(zone['Crane Pit'].incidents, 2) // SOS via Ali's assigned zone + breach located there
  assert.equal(zone['Crane Pit'].daysWithoutPpeViolation, 3)
  assert.equal(zone.Unattributed.incidents, 1)
  assert.deepEqual(
    m.byWorker.map((w) => [w.worker, w.incidents, w.ppeViolations]),
    [['Ali Raza', 2, 1], ['Sara Khan', 2, 0]],
  )
  const ali = m.attendance.find((a) => a.worker === 'Ali Raza')
  assert.deepEqual([ali.days, ali.onSiteMinutes, ali.idleMinutes], [2, 840, 90])
  assert.equal(Math.round(ali.idleShare * 100), 11)
  assert.equal(ali.medianFirstCheckIn, 8 * 60 + 30) // 08:00 and 09:00 PKT
})

test('empty period gives zeros, not optimistic percentages', () => {
  const m = computeComplianceMetrics({ alerts: [], zones: f.zones, workers: [], dailyActivity: [], ...period })
  assert.deepEqual(m.attendance, [])
  assert.equal(m.total, 0)
  assert.equal(m.resolution.medianMinutes, null)
  assert.deepEqual(m.byZone.map((z) => z.zone), ['Main Site', 'Crane Pit'])
  assert.ok(m.byZone.every((z) => z.incidents === 0 && z.daysWithoutPpeViolation === 3))
  assert.ok(!JSON.stringify(m).includes('%'))
})
