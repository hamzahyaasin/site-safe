const { formatDate, formatLabel, plural } = require('./format')
const { UNATTRIBUTED, zoneResolver } = require('./metrics')
const { jpegSize } = require('./jpeg')

// Evidence snapshots in reports (FR-34). A snapshot is the camera frame at the
// moment of the alert, kept by the API for its retention period.
const INCIDENT_EVIDENCE_LIMIT = 24
const ZONE_EVIDENCE_LIMIT = 2
const FETCH_CONCURRENCY = 4
const SEVERITY_RANK = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }

function hasSnapshot(alert) {
  return alert.source !== 'SIMULATED' && Boolean(alert.snapshot)
}

/** Most severe first, then newest: the incidents a reader most needs to see. */
function bySeverityThenNewest(a, b) {
  const rank = (x) => SEVERITY_RANK[x.severity] ?? 9
  return rank(a) - rank(b) || new Date(b.timestamp) - new Date(a.timestamp)
}

/** Incidents whose snapshots the incident report shows, in figure order. */
function incidentEvidence(alerts, limit = INCIDENT_EVIDENCE_LIMIT) {
  return alerts.filter(hasSnapshot).sort(bySeverityThenNewest).slice(0, limit)
}

/** Up to ``perZone`` snapshots per zone for the safety report, zones in the given order. */
function zoneEvidence(alerts, zones, workers, perZone = ZONE_EVIDENCE_LIMIT) {
  const zoneOf = zoneResolver(workers)
  const names = [...zones.map((z) => z.name), UNATTRIBUTED]
  const picked = []
  for (const name of names) {
    const inZone = alerts.filter((a) => hasSnapshot(a) && zoneOf(a) === name).sort(bySeverityThenNewest)
    picked.push(...inZone.slice(0, perZone).map((alert) => ({ alert, zone: name })))
  }
  return picked
}

/** Camera incidents with and without a snapshot (simulated alerts excluded). */
function snapshotCounts(alerts) {
  const camera = alerts.filter((a) => a.source === 'AI_CAMERA')
  const withSnapshot = camera.filter((a) => a.snapshot).length
  return { camera: camera.length, withSnapshot, without: camera.length - withSnapshot }
}

/**
 * Fetch each alert's snapshot; returns Map(alert id -> { data, width, height }).
 * A snapshot that cannot be fetched or read is left out and counted by the
 * report, so one missing image never stops a report.
 */
async function loadEvidence(alerts, fetchSnapshot) {
  const images = new Map()
  const queue = [...alerts]
  async function worker() {
    while (queue.length) {
      const alert = queue.shift()
      try {
        const data = await fetchSnapshot(alert.snapshot)
        const size = jpegSize(data)
        if (size) images.set(alert.id, { data, ...size })
      } catch {
        // Counted as "could not be loaded" by the template.
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(FETCH_CONCURRENCY, queue.length) }, worker))
  return images
}

/** Caption lines for one figure; the first is the heading line. */
function caption(alert, label, tz, zone) {
  const where = [alert.camera_id, zone || alert.zone_name].filter(Boolean)
  const model = alert.model_version
    ? `Model ${alert.model_version}${alert.confidence != null ? ` · confidence ${Number(alert.confidence).toFixed(2)}` : ''}`
    : null
  return [
    `${label} · ${formatLabel(alert.alert_type)} · ${formatLabel(alert.severity)} · ${alert.is_resolved ? 'Resolved' : 'Open'}`,
    `${formatDate(alert.timestamp, tz)} · ${where.length ? (where.length === 2 ? `${where[0]} (${where[1]})` : where[0]) : 'Camera not recorded'}`,
    alert.worker_name || 'Worker not identified',
    alert.description ? String(alert.description).slice(0, 140) : '—',
    ...(model ? [model] : []),
  ]
}

/**
 * Figures for the alerts that have a loaded image, labelled E1, E2, … in
 * order. Returns { items, labels: Map(alert id -> label), missing }.
 */
function figures(selected, images, tz) {
  const items = []
  const labels = new Map()
  let missing = 0
  for (const entry of selected) {
    const alert = entry.alert ?? entry
    const image = images.get(alert.id)
    if (!image) {
      missing += 1
      continue
    }
    const label = `E${items.length + 1}`
    labels.set(alert.id, label)
    items.push({
      label,
      image: image.data,
      width: image.width,
      height: image.height,
      alt: `${label}: ${formatLabel(alert.alert_type)} snapshot from ${alert.camera_id || 'camera'}`,
      caption: caption(alert, label, tz, entry.zone),
    })
  }
  return { items, labels, missing }
}

/**
 * The blocks of an evidence section and the figure labels (for the incident
 * log). ``evidence`` is null when snapshots were not requested. ``scope`` is
 * 'incident' (most severe overall) or 'zone' (a few per zone).
 */
function evidenceSection({ evidence, selected, alerts, tz, scope }) {
  if (!evidence) {
    return { blocks: [{ type: 'p', text: 'Camera snapshots were left out of this report when it was generated.' }], labels: null }
  }
  const counts = snapshotCounts(alerts)
  const { items, labels, missing } = figures(selected, evidence.images, tz)
  const gap = counts.without
    ? ` ${plural(counts.without, 'camera incident')} had no snapshot: snapshots were switched off, or removed after the retention period.`
    : ''
  if (!items.length && !missing) {
    return { blocks: [{ type: 'p', text: `No camera snapshots exist for this period.${gap}` }], labels }
  }
  let lead
  if (scope === 'zone') {
    lead = `Up to ${ZONE_EVIDENCE_LIMIT} camera snapshots per zone, its most severe incidents first (critical, then newest)`
  } else if (counts.withSnapshot > selected.length) {
    lead = `The ${selected.length} most severe of ${counts.withSnapshot} camera snapshots in this period (critical first, then newest); the rest are in the dashboard`
  } else {
    lead = `All ${plural(counts.withSnapshot, 'camera snapshot')} in this period, most severe first`
  }
  const text =
    `${lead}. Each is the frame the camera captured when it raised the alert, with the model that detected it.` +
    gap +
    (missing ? ` ${plural(missing, 'snapshot')} could not be loaded.` : '') +
    ' Snapshots can show people on site; share this report accordingly.'
  return { blocks: [{ type: 'p', text }, ...(items.length ? [{ type: 'figures', items }] : [])], labels }
}

module.exports = {
  INCIDENT_EVIDENCE_LIMIT,
  ZONE_EVIDENCE_LIMIT,
  bySeverityThenNewest,
  caption,
  evidenceSection,
  figures,
  incidentEvidence,
  loadEvidence,
  snapshotCounts,
  zoneEvidence,
}
