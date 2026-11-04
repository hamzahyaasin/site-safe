// Report metrics computed only from stored records.
//
// There is deliberately no "PPE compliance %": Site-Safe records the
// violations it detects, not the number of compliant observations, so no
// denominator exists and any percentage would overstate safety. Reports
// give counts, resolution times and violation-free days instead, and state
// how each is defined.

const ALERT_TYPES = ['PPE_VIOLATION', 'FALL', 'FIRE', 'SMOKE', 'DANGER_AREA', 'SOS', 'GAS', 'ZONE_BREACH', 'INACTIVITY', 'VEHICLE_PROXIMITY']
const SEVERITIES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
const UNATTRIBUTED = 'Unattributed'

function dayKey(iso, tz) {
  // en-CA formats as YYYY-MM-DD.
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: tz || 'UTC',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(iso))
}

function daysInPeriod(dateFrom, dateTo) {
  const days = []
  const cur = new Date(`${dateFrom}T00:00:00Z`)
  const end = new Date(`${dateTo}T00:00:00Z`)
  while (cur <= end) {
    days.push(cur.toISOString().slice(0, 10))
    cur.setUTCDate(cur.getUTCDate() + 1)
  }
  return days
}

/** Minutes after local midnight for an ISO time in ``tz``. */
function minutesOfDay(iso, tz) {
  const parts = new Intl.DateTimeFormat('en-GB', { timeZone: tz || 'UTC', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
    .formatToParts(new Date(iso))
  const get = (type) => Number(parts.find((p) => p.type === type).value)
  return get('hour') * 60 + get('minute')
}

function resolutionMinutes(alert) {
  if (!alert.is_resolved || !alert.resolved_at || !alert.timestamp) return null
  const mins = (new Date(alert.resolved_at) - new Date(alert.timestamp)) / 60000
  return Number.isFinite(mins) && mins >= 0 ? mins : null
}

function percentile(values, p) {
  if (!values.length) return null
  const sorted = [...values].sort((a, b) => a - b)
  const idx = (sorted.length - 1) * p
  const lo = Math.floor(idx)
  const hi = Math.ceil(idx)
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo)
}

function resolutionStats(alerts) {
  const times = alerts.map(resolutionMinutes).filter((v) => v !== null)
  return {
    resolvedWithTime: times.length,
    medianMinutes: percentile(times, 0.5),
    p90Minutes: percentile(times, 0.9),
    meanMinutes: times.length ? times.reduce((a, b) => a + b, 0) / times.length : null,
  }
}

function countBy(items, key, keys) {
  const out = Object.fromEntries((keys ?? []).map((k) => [k, 0]))
  for (const item of items) {
    const k = typeof key === 'function' ? key(item) : item[key] ?? 'UNKNOWN'
    out[k] = (out[k] ?? 0) + 1
  }
  return out
}

function splitSimulated(alerts) {
  const simulated = alerts.filter((a) => a.source === 'SIMULATED')
  const observed = alerts.filter((a) => a.source !== 'SIMULATED')
  return { observed, simulated }
}

/** Zone an alert counts under: where it happened (the API's zone_name, from
 * the camera or GPS position), else the worker's assigned zone, else
 * Unattributed. */
function zoneResolver(workers) {
  const workerZone = new Map(workers.map((w) => [w.id, w.zone_name || null]))
  return (alert) => alert.zone_name || (alert.worker ? workerZone.get(alert.worker) : null) || UNATTRIBUTED
}

function computeIncidentMetrics({ alerts, tz }) {
  const { observed, simulated } = splitSimulated(alerts)
  const resolved = observed.filter((a) => a.is_resolved).length
  return {
    total: observed.length,
    simulated: simulated.length,
    open: observed.length - resolved,
    resolved,
    critical: observed.filter((a) => a.severity === 'CRITICAL').length,
    identified: observed.filter((a) => a.worker).length,
    // Fire/smoke seen while a hot-work permit covered the zone (reduced severity).
    underHotWorkPermit: observed.filter((a) => a.hot_work_permit).length,
    byType: countBy(observed, 'alert_type', ALERT_TYPES),
    bySeverity: countBy(observed, 'severity', SEVERITIES),
    bySource: countBy(observed, 'source'),
    resolution: resolutionStats(observed),
    // Newest first, simulated rows included but labelled.
    log: [...alerts].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)),
    tz,
  }
}

function computeComplianceMetrics({ alerts, zones, workers, dailyActivity = [], dateFrom, dateTo, tz }) {
  const { observed, simulated } = splitSimulated(alerts)
  const zoneOf = zoneResolver(workers)
  const days = daysInPeriod(dateFrom, dateTo)

  const zoneNames = [...zones.map((z) => z.name)]
  if (observed.some((a) => zoneOf(a) === UNATTRIBUTED)) zoneNames.push(UNATTRIBUTED)

  const byZone = zoneNames.map((name) => {
    const zoneAlerts = observed.filter((a) => zoneOf(a) === name)
    const ppe = zoneAlerts.filter((a) => a.alert_type === 'PPE_VIOLATION')
    const ppeDays = new Set(ppe.map((a) => dayKey(a.timestamp, tz)))
    const zone = zones.find((z) => z.name === name)
    return {
      zone: name,
      riskLevel: zone?.risk_level ?? null,
      cameras: zone?.camera_ids?.length ?? 0,
      incidents: zoneAlerts.length,
      ppeViolations: ppe.length,
      critical: zoneAlerts.filter((a) => a.severity === 'CRITICAL').length,
      resolved: zoneAlerts.filter((a) => a.is_resolved).length,
      medianResolutionMinutes: resolutionStats(zoneAlerts).medianMinutes,
      daysWithoutPpeViolation: days.filter((d) => !ppeDays.has(d)).length,
    }
  })

  const byType = ALERT_TYPES.map((type) => {
    const typed = observed.filter((a) => a.alert_type === type)
    return {
      type,
      count: typed.length,
      resolved: typed.filter((a) => a.is_resolved).length,
      medianResolutionMinutes: resolutionStats(typed).medianMinutes,
    }
  })

  const workerNames = new Map(workers.map((w) => [w.id, w.name]))
  const byWorkerMap = new Map()
  for (const a of observed) {
    if (!a.worker) continue
    const row = byWorkerMap.get(a.worker) ?? {
      worker: a.worker_name || workerNames.get(a.worker) || `Worker #${a.worker}`,
      incidents: 0,
      ppeViolations: 0,
      critical: 0,
    }
    row.incidents += 1
    if (a.alert_type === 'PPE_VIOLATION') row.ppeViolations += 1
    if (a.severity === 'CRITICAL') row.critical += 1
    byWorkerMap.set(a.worker, row)
  }
  const byWorker = [...byWorkerMap.values()].sort((a, b) => b.incidents - a.incidents)

  // Attendance from the API's daily timelines (one row per worker-day with
  // evidence). Workers with no vest or badge evidence have no rows at all.
  const attendanceMap = new Map()
  for (const row of dailyActivity) {
    const a = attendanceMap.get(row.worker) ?? {
      worker: row.worker_name,
      days: 0,
      onSiteMinutes: 0,
      idleMinutes: 0,
      firstCheckIns: [],
    }
    a.days += 1
    a.onSiteMinutes += row.on_site_minutes
    a.idleMinutes += row.idle_minutes
    if (row.first_check_in) a.firstCheckIns.push(minutesOfDay(row.first_check_in, tz))
    attendanceMap.set(row.worker, a)
  }
  const attendance = [...attendanceMap.values()]
    .map((a) => ({
      worker: a.worker,
      days: a.days,
      onSiteMinutes: a.onSiteMinutes,
      idleMinutes: a.idleMinutes,
      idleShare: a.onSiteMinutes > 0 ? a.idleMinutes / a.onSiteMinutes : null,
      medianFirstCheckIn: percentile(a.firstCheckIns, 0.5),
    }))
    .sort((x, y) => x.worker.localeCompare(y.worker))

  return {
    periodDays: days.length,
    activeWorkers: workers.filter((w) => w.is_active).length,
    total: observed.length,
    simulated: simulated.length,
    // Alerts about a person no one could identify; a zone device's alert (a gas monitor) is about no person.
    unidentified: observed.filter((a) => !a.worker && !a.zone).length,
    resolution: resolutionStats(observed),
    byZone,
    byType,
    byWorker,
    attendance,
    dailyActivity,
    tz,
  }
}

module.exports = {
  ALERT_TYPES,
  SEVERITIES,
  UNATTRIBUTED,
  computeComplianceMetrics,
  computeIncidentMetrics,
  dayKey,
  minutesOfDay,
  daysInPeriod,
  percentile,
  resolutionMinutes,
  zoneResolver,
}
