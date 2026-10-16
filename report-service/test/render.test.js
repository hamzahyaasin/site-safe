const test = require('node:test')
const assert = require('node:assert/strict')

const { renderDocx } = require('../lib/render-docx')
const { pdfSafe, renderPdf } = require('../lib/render-pdf')
const { buildComplianceReport, METHOD } = require('../templates/compliance-report')
const { buildIncidentReport, MAX_LOG_ROWS } = require('../templates/incident-report')
const f = require('./fixtures')

const period = { dateFrom: '2026-10-14', dateTo: '2026-10-16', tz: 'Asia/Karachi' }

function pageCount(buffer) {
  return (buffer.toString('latin1').match(/\/Type\s*\/Page[^s]/g) || []).length
}

test('both report types render to DOCX and PDF', async () => {
  for (const model of [
    buildIncidentReport({ alerts: f.alerts, ...period }),
    buildComplianceReport({ ...f, ...period }),
  ]) {
    const docx = await renderDocx(model)
    assert.equal(docx.subarray(0, 2).toString(), 'PK')
    const pdf = await renderPdf(model)
    assert.equal(pdf.subarray(0, 5).toString(), '%PDF-')
    assert.ok(pageCount(pdf) >= 1)
  }
})

test('compliance report states its method and has no compliance percentage', () => {
  const model = buildComplianceReport({ ...f, ...period })
  const text = JSON.stringify(model)
  assert.ok(text.includes(METHOD[2]))
  assert.ok(!/Compliance %|\d+%/.test(text))
})

test('long incident logs paginate and disclose truncation', async () => {
  const many = Array.from({ length: MAX_LOG_ROWS + 5 }, (_, i) => ({
    ...f.alerts[0],
    id: 1000 + i,
    timestamp: new Date(Date.UTC(2026, 9, 15, 0, i % 60)).toISOString(),
  }))
  const model = buildIncidentReport({ alerts: many, ...period })
  const log = model.sections.find((s) => s.heading === 'Incident Log')
  assert.match(log.blocks[0].text, new RegExp(`Showing the ${MAX_LOG_ROWS} most recent of ${MAX_LOG_ROWS + 5}`))
  assert.equal(log.blocks[1].rows.length, MAX_LOG_ROWS)
  const pdf = await renderPdf(model)
  assert.ok(pageCount(pdf) > 10, `expected many pages, got ${pageCount(pdf)}`)
})

test('empty period renders', async () => {
  const model = buildIncidentReport({ alerts: [], ...period })
  assert.match(model.sections[0].blocks[0].text, /No incidents/)
  assert.equal((await renderPdf(model)).subarray(0, 5).toString(), '%PDF-')
})

test('pdf text is restricted to encodable characters', () => {
  assert.equal(pdfSafe('a → b ∞ 漢'), 'a -> b unlimited ?')
  assert.equal(pdfSafe('Café — “ok”'), 'Café — “ok”')
})
