const express = require('express')
const cors = require('cors')
const { Packer } = require('docx')

const { fetchActivityLogs, fetchAlerts, fetchWorkers, fetchZones } = require('./lib/django-api')
const { buildComplianceReport } = require('./templates/compliance-report')
const { buildIncidentReport } = require('./templates/incident-report')

const app = express()
const PORT = process.env.PORT || 3001

app.use(cors())
app.use(express.json())

const REPORT_TYPES = new Set(['INCIDENT', 'COMPLIANCE'])

function isValidDate(value) {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
}

function validateRequest(body) {
  const { report_type, date_from, date_to, api_token } = body ?? {}

  if (!REPORT_TYPES.has(report_type)) {
    return 'report_type must be INCIDENT or COMPLIANCE'
  }
  if (!isValidDate(date_from)) {
    return 'date_from must be YYYY-MM-DD'
  }
  if (!isValidDate(date_to)) {
    return 'date_to must be YYYY-MM-DD'
  }
  if (date_from > date_to) {
    return 'date_to must be on or after date_from'
  }
  if (!api_token || typeof api_token !== 'string') {
    return 'api_token is required'
  }

  return null
}

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'report-service' })
})

app.post('/generate', async (req, res) => {
  const validationError = validateRequest(req.body)
  if (validationError) {
    return res.status(400).json({ detail: validationError })
  }

  const { report_type, date_from, date_to, api_token } = req.body

  try {
    const alerts = await fetchAlerts(api_token, date_from, date_to)

    let document
    if (report_type === 'INCIDENT') {
      document = buildIncidentReport({
        alerts,
        dateFrom: date_from,
        dateTo: date_to,
      })
    } else {
      const [zones, workers, activityLogs] = await Promise.all([
        fetchZones(api_token),
        fetchWorkers(api_token),
        fetchActivityLogs(api_token, date_from, date_to),
      ])

      document = buildComplianceReport({
        alerts,
        zones,
        workers,
        activityLogs,
        dateFrom: date_from,
        dateTo: date_to,
      })
    }

    const buffer = await Packer.toBuffer(document)
    const filename = `${report_type.toLowerCase()}_report_${date_from}_${date_to}.docx`

    res.setHeader(
      'Content-Type',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`)
    return res.send(buffer)
  } catch (error) {
    const status = error.status && error.status >= 400 && error.status < 600 ? error.status : 502
    return res.status(status).json({
      detail: error.message || 'Failed to generate report',
    })
  }
})

app.listen(PORT, () => {
  console.log(`Report service listening on port ${PORT}`)
})
