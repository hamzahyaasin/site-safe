const test = require('node:test')
const assert = require('node:assert/strict')

const { createApp, validateRequest } = require('../lib/app')
const f = require('./fixtures')

function withServer(api, fn) {
  return new Promise((resolve, reject) => {
    const server = createApp(api).listen(0, async () => {
      try {
        await fn(`http://127.0.0.1:${server.address().port}`)
        resolve()
      } catch (e) {
        reject(e)
      } finally {
        server.close()
      }
    })
  })
}

const body = { report_type: 'COMPLIANCE', date_from: '2026-10-14', date_to: '2026-10-16', tz: 'Asia/Karachi', format: 'PDF', api_token: 't' }

test('validation', () => {
  assert.equal(validateRequest(body), null)
  assert.match(validateRequest({ ...body, format: 'XLS' }), /format/)
  assert.match(validateRequest({ ...body, tz: 'Mars/Base' }), /tz/)
  assert.match(validateRequest({ ...body, date_from: '2026-10-20' }), /on or after/)
  assert.match(validateRequest({ ...body, date_to: '2026-13-45' }), /date_to/)
})

test('generates a PDF and passes the period and time zone to the API', async () => {
  const calls = []
  const api = {
    fetchAlerts: async (...a) => (calls.push(a), f.alerts),
    fetchZones: async () => f.zones,
    fetchWorkers: async () => f.workers,
    fetchActivityLogs: async () => f.activityLogs,
  }
  await withServer(api, async (base) => {
    const r = await fetch(`${base}/generate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    assert.equal(r.status, 200)
    assert.equal(r.headers.get('content-type'), 'application/pdf')
    assert.match(r.headers.get('content-disposition'), /compliance_report_2026-10-14_2026-10-16\.pdf/)
    assert.equal(Buffer.from(await r.arrayBuffer()).subarray(0, 5).toString(), '%PDF-')
  })
  assert.deepEqual(calls[0], ['t', '2026-10-14', '2026-10-16', 'Asia/Karachi'])
})

test('upstream API failures are reported with their status', async () => {
  const failing = Object.assign(new Error('Django API error (403)'), { status: 403 })
  const api = { fetchAlerts: async () => { throw failing } }
  await withServer(api, async (base) => {
    const r = await fetch(`${base}/generate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...body, report_type: 'INCIDENT' }) })
    assert.equal(r.status, 403)
    assert.match((await r.json()).detail, /403/)
  })
})
