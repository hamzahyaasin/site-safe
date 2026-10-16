const { ALERT_TYPES, SEVERITIES, computeIncidentMetrics } = require('../lib/metrics')
const { formatDate, formatDuration, formatLabel, plural, was } = require('../lib/format')

// A report never silently drops rows: beyond this the log is cut and the
// report says so.
const MAX_LOG_ROWS = 1000

function buildIncidentReport({ alerts, dateFrom, dateTo, tz, generatedAt = new Date() }) {
  const m = computeIncidentMetrics({ alerts, tz })
  const shown = m.log.slice(0, MAX_LOG_ROWS)

  return {
    title: 'Site-Safe Incident Report',
    subtitle: 'Safety incidents recorded in the reporting period',
    meta: [
      `Reporting period: ${dateFrom} to ${dateTo} (${tz || 'UTC'})`,
      `Generated: ${formatDate(generatedAt.toISOString(), tz)}`,
    ],
    sections: [
      {
        heading: 'Summary',
        blocks: [
          {
            type: 'p',
            text:
              m.total === 0
                ? 'No incidents were recorded from cameras or vests in this period.'
                : `${plural(m.total, 'incident')} ${was(m.total)} recorded from cameras and vests: ${m.open} open and ${m.resolved} resolved, ${m.critical} of critical severity. ${m.identified} ${was(m.identified)} attributed to an identified worker.`,
          },
          ...(m.simulated
            ? [
                {
                  type: 'p',
                  text: `${plural(m.simulated, 'simulated test alert')} also ${m.simulated === 1 ? 'exists' : 'exist'} in this period. They are listed in the log but excluded from every figure.`,
                },
              ]
            : []),
          {
            type: 'table',
            headers: ['Measure', 'Value'],
            widths: [3, 2],
            rows: [
              ['Incidents (excluding simulated)', String(m.total)],
              ['Open', String(m.open)],
              ['Resolved', String(m.resolved)],
              ['Median time to resolve', formatDuration(m.resolution.medianMinutes)],
              ['90th percentile time to resolve', formatDuration(m.resolution.p90Minutes)],
            ],
          },
        ],
      },
      {
        heading: 'Incidents by Type and Severity',
        blocks: [
          {
            type: 'table',
            headers: ['Type', 'Count'],
            widths: [3, 1],
            rows: ALERT_TYPES.map((t) => [formatLabel(t), String(m.byType[t] ?? 0)]),
          },
          {
            type: 'table',
            headers: ['Severity', 'Count'],
            widths: [3, 1],
            rows: SEVERITIES.map((s) => [formatLabel(s), String(m.bySeverity[s] ?? 0)]),
          },
        ],
      },
      {
        heading: 'Incident Log',
        blocks: [
          {
            type: 'p',
            text:
              m.log.length > MAX_LOG_ROWS
                ? `Showing the ${MAX_LOG_ROWS} most recent of ${m.log.length} entries; narrow the period for the full list.`
                : `All ${plural(m.log.length, 'entry')}, newest first. Times are in ${tz || 'UTC'}.`,
          },
          {
            type: 'table',
            headers: ['Time', 'Type', 'Severity', 'Worker', 'Camera / Source', 'Status', 'Description'],
            widths: [1.6, 1.3, 0.9, 1.2, 1.2, 0.8, 2.6],
            rows: shown.length
              ? shown.map((a) => [
                  formatDate(a.timestamp, tz),
                  formatLabel(a.alert_type),
                  formatLabel(a.severity),
                  a.worker_name || 'Not identified',
                  a.source === 'SIMULATED' ? 'Simulated' : a.camera_id || formatLabel(a.source),
                  a.is_resolved ? 'Resolved' : 'Open',
                  a.description ? String(a.description).slice(0, 160) : '—',
                ])
              : [['—', '—', '—', '—', '—', '—', 'No incidents in period']],
          },
        ],
      },
    ],
  }
}

module.exports = { buildIncidentReport, MAX_LOG_ROWS }
