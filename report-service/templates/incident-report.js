const { Document } = require('docx')
const {
  bodyText,
  bulletItem,
  dataTable,
  formatDate,
  formatLabel,
  sectionHeading,
  titlePage,
} = require('./shared')

function countByField(items, field) {
  return items.reduce((acc, item) => {
    const key = item[field] ?? 'UNKNOWN'
    acc[key] = (acc[key] ?? 0) + 1
    return acc
  }, {})
}

function severityChartDescription(bySeverity, total) {
  if (total === 0) {
    return 'No incidents were recorded during this reporting period.'
  }

  const order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
  const parts = order
    .filter((level) => bySeverity[level])
    .map((level) => {
      const count = bySeverity[level]
      const pct = ((count / total) * 100).toFixed(1)
      const barLength = Math.max(1, Math.round((count / total) * 20))
      const bar = '█'.repeat(barLength)
      return `${formatLabel(level)}: ${count} (${pct}%) ${bar}`
    })

  return [
    'Severity distribution (text representation of chart data):',
    ...parts,
    `Total incidents analysed: ${total}.`,
  ].join('\n')
}

function buildIncidentReport({ alerts, dateFrom, dateTo }) {
  const total = alerts.length
  const unresolved = alerts.filter((alert) => !alert.is_resolved).length
  const resolved = total - unresolved
  const critical = alerts.filter((alert) => alert.severity === 'CRITICAL').length
  const byType = countByField(alerts, 'alert_type')
  const bySeverity = countByField(alerts, 'severity')
  const bySource = countByField(alerts, 'source')

  const tableRows = alerts.slice(0, 500).map((alert) => [
    formatDate(alert.timestamp),
    formatLabel(alert.alert_type),
    alert.severity ?? '—',
    alert.worker_name ?? '—',
    formatLabel(alert.source),
    alert.is_resolved ? 'Resolved' : 'Open',
    alert.description ? String(alert.description).slice(0, 80) : '—',
  ])

  const children = [
    ...titlePage('Site-Safe Incident Report', 'Safety Incident Analysis', [
      `Reporting period: ${dateFrom} to ${dateTo}`,
      `Generated: ${new Date().toLocaleString()}`,
      'Confidential — Internal Use Only',
    ]),
    sectionHeading('Executive Summary'),
    bodyText(
      `This report summarises ${total} safety incident${total === 1 ? '' : 's'} recorded between ${dateFrom} and ${dateTo}.`,
    ),
    bulletItem(`Total incidents: ${total}`),
    bulletItem(`Open incidents: ${unresolved}`),
    bulletItem(`Resolved incidents: ${resolved}`),
    bulletItem(`Critical severity incidents: ${critical}`),
    bulletItem(`Resolution rate: ${total ? ((resolved / total) * 100).toFixed(1) : '100.0'}%`),

    sectionHeading('Incidents by Type'),
    ...Object.entries(byType).map(([type, count]) => bulletItem(`${formatLabel(type)}: ${count}`)),

    sectionHeading('Incidents by Source'),
    ...Object.entries(bySource).map(([source, count]) => bulletItem(`${formatLabel(source)}: ${count}`)),

    sectionHeading('Incident Log'),
    bodyText('Detailed listing of all incidents within the reporting period (most recent first).'),
    dataTable(
      ['Timestamp', 'Type', 'Severity', 'Worker', 'Source', 'Status', 'Description'],
      tableRows.length ? tableRows : [['—', '—', '—', '—', '—', '—', 'No incidents in period']],
      [1800, 1200, 900, 1200, 1100, 900, 1900],
    ),

    sectionHeading('Severity Breakdown'),
    bodyText(severityChartDescription(bySeverity, total)),
    ...Object.entries(bySeverity).map(([severity, count]) =>
      bulletItem(`${formatLabel(severity)}: ${count} incident${count === 1 ? '' : 's'}`),
    ),
  ]

  return new Document({
    sections: [{ properties: {}, children }],
  })
}

module.exports = { buildIncidentReport }
