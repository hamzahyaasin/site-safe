const express = require('express')

const { fetchAlerts, fetchDailyActivity, fetchSnapshot, fetchWorkers, fetchZones } = require('./django-api')
const { incidentEvidence, loadEvidence, zoneEvidence } = require('./evidence')
const { renderDocx } = require('./render-docx')
const { renderPdf } = require('./render-pdf')
const { buildComplianceReport } = require('../templates/compliance-report')
const { buildIncidentReport } = require('../templates/incident-report')

const REPORT_TYPES = new Set(['INCIDENT', 'COMPLIANCE'])
const FORMATS = {
  DOCX: {
    render: renderDocx,
    extension: 'docx',
    contentType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  },
  PDF: { render: renderPdf, extension: 'pdf', contentType: 'application/pdf' },
}

function isValidDate(value) {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value))
}

function isValidTimeZone(tz) {
  try {
    new Intl.DateTimeFormat('en', { timeZone: tz })
    return true
  } catch {
    return false
  }
}

function validateRequest(body) {
  const { report_type, date_from, date_to, api_token, format = 'DOCX', tz = '', include_evidence = true } = body ?? {}
  if (!REPORT_TYPES.has(report_type)) return 'report_type must be INCIDENT or COMPLIANCE'
  if (!FORMATS[format]) return 'format must be DOCX or PDF'
  if (!isValidDate(date_from)) return 'date_from must be YYYY-MM-DD'
  if (!isValidDate(date_to)) return 'date_to must be YYYY-MM-DD'
  if (date_from > date_to) return 'date_to must be on or after date_from'
  if (tz && !isValidTimeZone(tz)) return 'tz must be an IANA time zone'
  if (typeof include_evidence !== 'boolean') return 'include_evidence must be true or false'
  if (!api_token || typeof api_token !== 'string') return 'api_token is required'
  return null
}

/** Snapshots for the selected alerts, or null when evidence was not requested. */
async function evidenceFor(selected, includeEvidence, apiToken, api) {
  if (!includeEvidence) return null
  const alerts = selected.map((entry) => entry.alert ?? entry)
  return { images: await loadEvidence(alerts, (path) => api.fetchSnapshot(apiToken, path)) }
}

async function buildModel({ report_type, date_from, date_to, api_token, tz, include_evidence = true }, api) {
  const alerts = await api.fetchAlerts(api_token, date_from, date_to, tz)
  if (report_type === 'INCIDENT') {
    const evidence = await evidenceFor(incidentEvidence(alerts), include_evidence, api_token, api)
    return buildIncidentReport({ alerts, evidence, dateFrom: date_from, dateTo: date_to, tz })
  }
  const [zones, workers, dailyActivity] = await Promise.all([
    api.fetchZones(api_token),
    api.fetchWorkers(api_token),
    api.fetchDailyActivity(api_token, date_from, date_to, tz),
  ])
  const evidence = await evidenceFor(zoneEvidence(alerts, zones, workers), include_evidence, api_token, api)
  return buildComplianceReport({ alerts, zones, workers, dailyActivity, evidence, dateFrom: date_from, dateTo: date_to, tz })
}

function createApp(api = { fetchAlerts, fetchDailyActivity, fetchSnapshot, fetchWorkers, fetchZones }) {
  const app = express()
  // Called only by the Django backend, never by browsers, so no CORS.
  app.use(express.json())

  app.get('/health', (_req, res) => {
    res.json({ status: 'ok', service: 'report-service' })
  })

  app.post('/generate', async (req, res) => {
    const validationError = validateRequest(req.body)
    if (validationError) return res.status(400).json({ detail: validationError })

    const { report_type, date_from, date_to, format = 'DOCX', tz = '' } = req.body
    const out = FORMATS[format]
    try {
      const model = await buildModel({ ...req.body, tz: tz || 'UTC' }, api)
      const buffer = await out.render(model)
      const filename = `${report_type.toLowerCase()}_report_${date_from}_${date_to}.${out.extension}`
      res.setHeader('Content-Type', out.contentType)
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`)
      return res.send(buffer)
    } catch (error) {
      const status = error.status && error.status >= 400 && error.status < 600 ? error.status : 502
      return res.status(status).json({ detail: error.message || 'Failed to generate report' })
    }
  })

  return app
}

module.exports = { createApp, validateRequest }
