const { filterByDateRange } = require('../templates/shared')

const DEFAULT_API_BASE = 'http://localhost:8000/api/'

async function djangoFetch(path, apiToken) {
  const base = (process.env.DJANGO_API_URL || DEFAULT_API_BASE).replace(/\/?$/, '/')
  const url = `${base}${path.replace(/^\//, '')}`

  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${apiToken}`,
      Accept: 'application/json',
    },
  })

  if (!response.ok) {
    const body = await response.text()
    const error = new Error(`Django API error (${response.status})`)
    error.status = response.status
    error.body = body
    throw error
  }

  return response.json()
}

function unwrapList(data) {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

async function fetchAlerts(apiToken, dateFrom, dateTo) {
  const data = await djangoFetch('alerts/', apiToken)
  return filterByDateRange(unwrapList(data), dateFrom, dateTo, 'timestamp')
}

async function fetchZones(apiToken) {
  const data = await djangoFetch('v1/zones/', apiToken)
  return unwrapList(data)
}

async function fetchWorkers(apiToken) {
  const data = await djangoFetch('workers/', apiToken)
  return unwrapList(data)
}

async function fetchActivityLogs(apiToken, dateFrom, dateTo) {
  const data = await djangoFetch('v1/activity/', apiToken)
  return filterByDateRange(unwrapList(data), dateFrom, dateTo, 'timestamp')
}

module.exports = {
  fetchAlerts,
  fetchZones,
  fetchWorkers,
  fetchActivityLogs,
}
