const test = require('node:test')
const assert = require('node:assert/strict')

const ev = require('../lib/evidence')
const { jpegSize } = require('../lib/jpeg')
const { renderDocx } = require('../lib/render-docx')
const { renderPdf } = require('../lib/render-pdf')
const { buildComplianceReport } = require('../templates/compliance-report')
const { buildIncidentReport } = require('../templates/incident-report')
const f = require('./fixtures')

const period = { dateFrom: '2026-10-14', dateTo: '2026-10-16', tz: 'Asia/Karachi' }
const snap = (id) => `/api/alerts/${id}/snapshot/`
// Camera alerts 1, 2 and 4 have snapshots; 4 is the only critical one.
const alerts = f.alerts.map((a) =>
  a.source === 'AI_CAMERA' ? { ...a, snapshot: snap(a.id), model_version: 'sitesafe_v5.pt@7e8e092d0603', confidence: 0.61 } : a,
)
const allImages = (list) => new Map(list.map((a) => [a.id, { data: f.JPEG, width: 64, height: 48 }]))

test('reads the size of a JPEG and rejects anything else', () => {
  assert.deepEqual(jpegSize(f.JPEG), { width: 64, height: 48 })
  assert.equal(jpegSize(Buffer.from('not a jpeg')), null)
  assert.equal(jpegSize(f.JPEG.subarray(0, 20)), null, 'truncated before the frame header')
  assert.equal(jpegSize('string'), null)
})

test('incident evidence: critical first, then newest; simulated and snapshot-less alerts never', () => {
  const simulated = { ...alerts[0], id: 99, source: 'SIMULATED', severity: 'CRITICAL', snapshot: snap(99) }
  const picked = ev.incidentEvidence([...alerts, simulated])
  assert.deepEqual(picked.map((a) => a.id), [4, 2, 1])
  assert.deepEqual(ev.incidentEvidence(alerts, 2).map((a) => a.id), [4, 2])
})

test('zone evidence: at most two per zone, zones in order, unattributed last', () => {
  const more = [...alerts, { ...alerts[0], id: 7, severity: 'CRITICAL', snapshot: snap(7) }]
  const picked = ev.zoneEvidence(more, f.zones, f.workers)
  assert.deepEqual(
    picked.map((p) => [p.zone, p.alert.id]),
    [
      ['Main Site', 7],
      ['Main Site', 2],
      ['Unattributed', 4],
    ],
  )
})

test('a snapshot that cannot be fetched or read is left out, not fatal', async () => {
  const fetched = []
  const images = await ev.loadEvidence(ev.incidentEvidence(alerts), async (path) => {
    fetched.push(path)
    if (path === snap(2)) throw Object.assign(new Error('gone'), { status: 404 })
    if (path === snap(1)) return Buffer.from('<html>login</html>')
    return f.JPEG
  })
  assert.deepEqual(fetched.sort(), [snap(1), snap(2), snap(4)])
  assert.deepEqual([...images.keys()], [4])
  assert.deepEqual({ ...images.get(4), data: undefined }, { data: undefined, width: 64, height: 48 })
})

test('incident report: numbered figures, captions, and the log points to them', () => {
  const model = buildIncidentReport({ alerts, evidence: { images: allImages(alerts) }, ...period })
  const section = model.sections.find((s) => s.heading === 'Evidence')
  assert.match(section.blocks[0].text, /All 3 camera snapshots in this period, most severe first/)
  assert.match(section.blocks[0].text, /share this report accordingly/)
  const figs = section.blocks[1]
  assert.equal(figs.type, 'figures')
  assert.deepEqual(figs.items.map((i) => i.label), ['E1', 'E2', 'E3'])
  assert.deepEqual(figs.items[0].caption, [
    'E1 · Fall · Critical · Open',
    '15 Oct 2026, 15:00 · CAM-09',
    'Sara Khan',
    '—',
    'Model sitesafe_v5.pt@7e8e092d0603 · confidence 0.61',
  ])
  const log = model.sections.find((s) => s.heading === 'Incident Log').blocks[1]
  assert.equal(log.headers.at(-1), 'Figure')
  const evidenceOf = Object.fromEntries(log.rows.map((r) => [r[0], r.at(-1)]))
  assert.equal(evidenceOf['15 Oct 2026, 15:00'], 'E1')
  assert.equal(evidenceOf['15 Oct 2026, 13:00'], '—', 'the vest SOS has no snapshot')
})

test('the report says what is missing instead of hiding it', () => {
  const noSnapshot = { ...alerts[0], id: 8, snapshot: null }
  const images = allImages([alerts[3]]) // only the fall loaded
  const model = buildIncidentReport({ alerts: [...alerts, noSnapshot], evidence: { images }, ...period })
  const text = model.sections.find((s) => s.heading === 'Evidence').blocks[0].text
  assert.match(text, /1 camera incident had no snapshot/)
  assert.match(text, /2 snapshots could not be loaded/)

  const none = buildIncidentReport({ alerts: f.alerts, evidence: { images: new Map() }, ...period })
  assert.match(none.sections.find((s) => s.heading === 'Evidence').blocks[0].text, /No camera snapshots exist/)

  const off = buildIncidentReport({ alerts, evidence: null, ...period })
  assert.match(off.sections.find((s) => s.heading === 'Evidence').blocks[0].text, /left out of this report/)
  assert.notEqual(off.sections.find((s) => s.heading === 'Incident Log').blocks[1].headers.at(-1), 'Figure')
})

test('safety report: evidence by zone names the zone in each caption', () => {
  const model = buildComplianceReport({ ...f, alerts, evidence: { images: allImages(alerts) }, ...period })
  const section = model.sections.find((s) => s.heading === 'Evidence by Zone')
  assert.match(section.blocks[0].text, /Up to 2 camera snapshots per zone/)
  const captions = section.blocks[1].items.map((i) => i.caption[1])
  assert.deepEqual(captions, ['15 Oct 2026, 00:30 · CAM-01 (Main Site)', '14 Oct 2026, 10:00 · CAM-01 (Main Site)', '15 Oct 2026, 15:00 · CAM-09 (Unattributed)'])
})

test('figures are embedded as images in DOCX and PDF', async () => {
  const model = buildIncidentReport({ alerts, evidence: { images: allImages(alerts) }, ...period })
  const docx = await renderDocx(model)
  // Zip entry names are stored uncompressed, so embedded images are visible as word/media/ entries.
  assert.match(docx.toString('latin1'), /word\/media\/[^/\s]+\.(jpg|jpeg)/)
  const pdf = await renderPdf(model)
  assert.equal((pdf.toString('latin1').match(/\/Subtype \/Image/g) || []).length, 3)
})

test('a snapshot is only ever fetched from the API host, so the token stays there', async () => {
  const { fetchSnapshot } = require('../lib/django-api')
  await assert.rejects(fetchSnapshot('t', 'https://elsewhere.example/a.jpg'), /not on the API host/)
  await assert.rejects(fetchSnapshot('t', '//elsewhere.example/a.jpg'), /not on the API host/)
})
