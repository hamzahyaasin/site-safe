const { UNATTRIBUTED, computeComplianceMetrics } = require('../lib/metrics')
const { formatDate, formatDuration, formatLabel, plural, was } = require('../lib/format')

const METHOD = [
  'Figures count recorded incidents, excluding simulated test alerts.',
  `An incident is counted under the zone where it happened: the camera's zone, or the zone containing its GPS position. If neither is known, the identified worker's assigned zone is used, and failing that it is listed as "${UNATTRIBUTED}".`,
  'No PPE compliance percentage is given. Site-Safe records the violations it detects, not the number of compliant observations, so no valid denominator exists.',
  'Instead the report gives days without a recorded PPE violation. Such a day can also mean the zone was not observed, for example camera offline or no work, so it is not evidence of compliance on its own.',
  'Time to resolve runs from when an incident was raised to when it was marked resolved in the dashboard.',
]

function buildComplianceReport({ alerts, zones, workers, activityLogs, dateFrom, dateTo, tz, generatedAt = new Date() }) {
  const m = computeComplianceMetrics({ alerts, zones, workers, activityLogs, dateFrom, dateTo, tz })

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
        heading: 'Worker Activity',
        blocks: [
          {
            type: 'p',
            text: `${plural(m.activityLogCount, 'activity record')} in the period. Zone entries come from vest GPS; check-ins and idle periods appear only where they were recorded.`,
          },
          {
            type: 'table',
            headers: ['Worker', 'Check-ins', 'Check-outs', 'Zone entries', 'Idle periods'],
            widths: [2, 1, 1, 1, 1],
            rows: m.activity.length
              ? m.activity.map((r) => [r.worker, String(r.checkIns), String(r.checkOuts), String(r.zoneEntries), String(r.idlePeriods)])
              : [['No activity recorded', '—', '—', '—', '—']],
          },
        ],
      },
    ],
  }
}

module.exports = { buildComplianceReport, METHOD }
