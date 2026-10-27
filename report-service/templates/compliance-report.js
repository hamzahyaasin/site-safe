const { UNATTRIBUTED, computeComplianceMetrics } = require('../lib/metrics')
const { evidenceSection, zoneEvidence } = require('../lib/evidence')
const { formatDate, formatDuration, formatLabel, plural, was } = require('../lib/format')

const METHOD = [
  'Figures count recorded incidents, excluding simulated test alerts.',
  `An incident is counted under the zone where it happened: the camera's zone, or the zone containing its GPS position. If neither is known, the identified worker's assigned zone is used, and failing that it is listed as "${UNATTRIBUTED}".`,
  'No PPE compliance percentage is given. Site-Safe records the violations it detects, not the number of compliant observations, so no valid denominator exists.',
  'Instead the report gives days without a recorded PPE violation. Such a day can also mean the zone was not observed, for example camera offline or no work, so it is not evidence of compliance on its own.',
  'Time to resolve runs from when an incident was raised to when it was marked resolved in the dashboard.',
]

/** ``evidence`` is { images } of loaded snapshots, or null when they were not requested. */
function buildComplianceReport({ alerts, zones, workers, dailyActivity = [], evidence = null, dateFrom, dateTo, tz, generatedAt = new Date() }) {
  const m = computeComplianceMetrics({ alerts, zones, workers, dailyActivity, dateFrom, dateTo, tz })
  const ev = evidenceSection({ evidence, selected: zoneEvidence(alerts, zones, workers), alerts, tz, scope: 'zone' })
  const clock = (mins) => (mins === null ? '—' : `${String(Math.floor(mins / 60)).padStart(2, '0')}:${String(Math.round(mins % 60)).padStart(2, '0')}`)

  return {
    title: 'Site-Safe Safety Performance Report',
    subtitle: 'Incidents, PPE violations and response by zone',
    meta: [
      `Reporting period: ${dateFrom} to ${dateTo}, ${plural(m.periodDays, 'day')} (${tz || 'UTC'})`,
      `Generated: ${formatDate(generatedAt.toISOString(), tz)}`,
    ],
    sections: [
      {
        heading: 'Summary',
        blocks: [
          {
            type: 'p',
            text: `${plural(m.total, 'incident')} across ${plural(zones.length, 'zone')} and ${plural(m.activeWorkers, 'active worker')}. ${m.unidentified} ${was(m.unidentified)} not attributed to a worker. Median time to resolve: ${formatDuration(m.resolution.medianMinutes)} (${m.resolution.resolvedWithTime} resolved).`,
          },
          ...(m.simulated
            ? [{ type: 'p', text: `${plural(m.simulated, 'simulated test alert')} ${was(m.simulated)} excluded.` }]
            : []),
        ],
      },
      {
        heading: 'Method and Definitions',
        blocks: [{ type: 'list', items: METHOD }],
      },
      {
        heading: 'Zones',
        blocks: [
          {
            type: 'table',
            headers: ['Zone', 'Risk', 'Incidents', 'PPE violations', 'Critical', 'Resolved', 'Median resolve', `Days without PPE violation (of ${m.periodDays})`],
            widths: [1.6, 1, 0.9, 1, 0.8, 0.9, 1.1, 1.4],
            rows: m.byZone.length
              ? m.byZone.map((z) => [
                  z.zone,
                  z.riskLevel ? formatLabel(z.riskLevel) : '—',
                  String(z.incidents),
                  String(z.ppeViolations),
                  String(z.critical),
                  String(z.resolved),
                  formatDuration(z.medianResolutionMinutes),
                  String(z.daysWithoutPpeViolation),
                ])
              : [['No zones defined', '—', '0', '0', '0', '0', '—', '—']],
          },
        ],
      },
      { heading: 'Evidence by Zone', blocks: ev.blocks },
      {
        heading: 'Incident Types',
        blocks: [
          {
            type: 'table',
            headers: ['Type', 'Incidents', 'Resolved', 'Median resolve'],
            widths: [2, 1, 1, 1.2],
            rows: m.byType.map((t) => [formatLabel(t.type), String(t.count), String(t.resolved), formatDuration(t.medianResolutionMinutes)]),
          },
        ],
      },
      {
        heading: 'Identified Workers',
        blocks: [
          {
            type: 'p',
            text: 'Incidents attributed to a worker by QR badge, vest or manual entry. Unidentified incidents are not apportioned to anyone.',
          },
          {
            type: 'table',
            headers: ['Worker', 'Incidents', 'PPE violations', 'Critical'],
            widths: [2, 1, 1, 1],
            rows: m.byWorker.length
              ? m.byWorker.map((w) => [w.worker, String(w.incidents), String(w.ppeViolations), String(w.critical)])
              : [['No incidents attributed to a worker', '—', '—', '—']],
          },
        ],
      },
      {
        heading: 'Worker Attendance and Idle Time',
        blocks: [
          {
            type: 'p',
            text: 'Sessions start on the first vest report or QR badge sighting of a worker, and end automatically once the worker has not been seen for a set interval, dated to the last sighting. Idle time is time an identified worker stayed still in camera view beyond the inactivity timeout. Workers with neither a vest nor a readable badge have no attendance evidence and do not appear here; this is not absence.',
          },
          {
            type: 'table',
            headers: ['Worker', 'Days with evidence', 'Time on site', 'Idle time', 'Idle share', 'Median first check-in'],
            widths: [2, 1, 1.2, 1.2, 1, 1.3],
            rows: m.attendance.length
              ? m.attendance.map((a) => [
                  a.worker,
                  String(a.days),
                  formatDuration(a.onSiteMinutes),
                  formatDuration(a.idleMinutes),
                  a.idleShare === null ? '—' : `${Math.round(a.idleShare * 100)}%`,
                  clock(a.medianFirstCheckIn),
                ])
              : [['No attendance evidence in this period', '—', '—', '—', '—', '—']],
          },
        ],
      },
      {
        heading: 'Daily Attendance',
        level: 2,
        blocks: [
          {
            type: 'table',
            headers: ['Date', 'Worker', 'First in', 'Last out', 'On site', 'Idle'],
            widths: [1.1, 1.8, 1, 1, 1, 1],
            rows: m.dailyActivity.length
              ? m.dailyActivity.map((d) => [
                  d.date,
                  d.worker_name,
                  d.first_check_in ? formatDate(d.first_check_in, tz).split(', ').pop() : 'carried over',
                  d.still_open ? 'still on site' : d.last_check_out ? formatDate(d.last_check_out, tz).split(', ').pop() : '—',
                  formatDuration(d.on_site_minutes),
                  formatDuration(d.idle_minutes),
                ])
              : [['—', 'No attendance evidence', '—', '—', '—', '—']],
          },
        ],
      },
    ],
  }
}

module.exports = { buildComplianceReport, METHOD }
