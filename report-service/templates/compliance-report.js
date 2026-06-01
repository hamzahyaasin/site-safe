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

function responseTimeMinutes(alert) {
  if (!alert.is_resolved || !alert.resolved_at || !alert.timestamp) {
    return null
  }
  const start = new Date(alert.timestamp).getTime()
  const end = new Date(alert.resolved_at).getTime()
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) {
    return null
  }
  return (end - start) / 60000
}

function formatDuration(minutes) {
  if (minutes == null) return '—'
  if (minutes < 60) return `${Math.round(minutes)} min`
  const hours = Math.floor(minutes / 60)
  const mins = Math.round(minutes % 60)
  return `${hours}h ${mins}m`
}

function average(values) {
  if (!values.length) return null
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

function buildZoneCompliance(zones, workers, alerts) {
  return zones.map((zone) => {
    const zoneWorkers = workers.filter((worker) => worker.zone === zone.id && worker.is_active)
    const workerIds = new Set(zoneWorkers.map((worker) => worker.id))
    const ppeViolations = alerts.filter(
      (alert) => alert.alert_type === 'PPE_VIOLATION' && workerIds.has(alert.worker),
    ).length

    const compliancePct =
      zoneWorkers.length === 0
        ? 100
        : Math.max(0, Math.min(100, Math.round(100 - (ppeViolations / zoneWorkers.length) * 25)))

    return {
      zoneName: zone.name,
      workerCount: zoneWorkers.length,
      ppeViolations,
      compliancePct,
    }
  })
}

function buildWorkerActivitySummary(activityLogs) {
  const byAction = activityLogs.reduce((acc, log) => {
    const action = log.action ?? 'UNKNOWN'
    acc[action] = (acc[action] ?? 0) + 1
    return acc
  }, {})

  const byWorker = activityLogs.reduce((acc, log) => {
    const name = log.worker_name ?? `Worker #${log.worker}`
    if (!acc[name]) {
      acc[name] = { checkIns: 0, checkOuts: 0, zoneEvents: 0, idleEvents: 0, total: 0 }
    }
    acc[name].total += 1
    if (log.action === 'CHECK_IN') acc[name].checkIns += 1
    if (log.action === 'CHECK_OUT') acc[name].checkOuts += 1
    if (log.action === 'ZONE_ENTER' || log.action === 'ZONE_EXIT') acc[name].zoneEvents += 1
    if (log.action === 'IDLE_START' || log.action === 'IDLE_END') acc[name].idleEvents += 1
    return acc
  }, {})

  return { byAction, byWorker }
}

function buildComplianceReport({ alerts, zones, workers, activityLogs, dateFrom, dateTo }) {
  const zoneCompliance = buildZoneCompliance(zones, workers, alerts)
  const { byAction, byWorker } = buildWorkerActivitySummary(activityLogs)

  const responseTimes = alerts
    .map((alert) => responseTimeMinutes(alert))
    .filter((value) => value != null)

  const avgResponse = average(responseTimes)
  const resolvedAlerts = alerts.filter((alert) => alert.is_resolved && alert.resolved_at)

  const responseRows = resolvedAlerts.slice(0, 200).map((alert) => [
    formatDate(alert.timestamp),
    formatLabel(alert.alert_type),
    alert.worker_name ?? '—',
    formatDate(alert.resolved_at),
    formatDuration(responseTimeMinutes(alert)),
  ])

  const zoneRows = zoneCompliance.map((row) => [
    row.zoneName,
    String(row.workerCount),
    String(row.ppeViolations),
    `${row.compliancePct}%`,
  ])

  const workerRows = Object.entries(byWorker)
    .sort((a, b) => b[1].total - a[1].total)
    .slice(0, 50)
    .map(([name, stats]) => [
      name,
      String(stats.checkIns),
      String(stats.checkOuts),
      String(stats.zoneEvents),
      String(stats.idleEvents),
      String(stats.total),
    ])

  const children = [
    ...titlePage('Site-Safe Compliance Report', 'PPE & Operational Compliance Analysis', [
      `Reporting period: ${dateFrom} to ${dateTo}`,
      `Generated: ${new Date().toLocaleString()}`,
      'Confidential — Internal Use Only',
    ]),

    sectionHeading('Overview'),
    bodyText(
      `Compliance metrics for ${zones.length} zone${zones.length === 1 ? '' : 's'}, ${workers.filter((worker) => worker.is_active).length} active workers, and ${alerts.length} alert${alerts.length === 1 ? '' : 's'} in the selected period.`,
    ),
    bulletItem(`Average alert response time: ${formatDuration(avgResponse)}`),
    bulletItem(`Resolved alerts with response data: ${responseTimes.length}`),
    bulletItem(`Total activity log entries: ${activityLogs.length}`),

    sectionHeading('PPE Compliance by Zone'),
    bodyText(
      'Estimated PPE compliance is derived from active workers assigned to each zone versus PPE violation alerts attributed to those workers during the reporting period.',
    ),
    dataTable(
      ['Zone', 'Active Workers', 'PPE Violations', 'Compliance %'],
      zoneRows.length ? zoneRows : [['—', '0', '0', '100%']],
      [2500, 1500, 1500, 1500],
    ),

    sectionHeading('Worker Activity Summary'),
    bodyText('Aggregate worker activity derived from site activity logs.'),
    ...Object.entries(byAction).map(([action, count]) =>
      bulletItem(`${formatLabel(action)}: ${count}`),
    ),
    sectionHeading('Activity by Worker', 2),
    dataTable(
      ['Worker', 'Check-ins', 'Check-outs', 'Zone Events', 'Idle Events', 'Total'],
      workerRows.length ? workerRows : [['—', '0', '0', '0', '0', '0']],
      [2200, 1000, 1000, 1100, 1100, 1000],
    ),

    sectionHeading('Alert Response Times'),
    bodyText(
      `Response time is measured from alert creation to resolution. Average response time across ${responseTimes.length} resolved alert${responseTimes.length === 1 ? '' : 's'}: ${formatDuration(avgResponse)}.`,
    ),
    dataTable(
      ['Raised', 'Type', 'Worker', 'Resolved', 'Response Time'],
      responseRows.length ? responseRows : [['—', '—', '—', '—', 'No resolved alerts in period']],
      [1800, 1300, 1400, 1800, 1200],
    ),
  ]

  return new Document({
    sections: [{ properties: {}, children }],
  })
}

module.exports = { buildComplianceReport }
