const DEFAULT_API_BASE = 'http://localhost:8000/api/'

async function djangoFetch(path, apiToken, params = {}) {
  const base = (process.env.DJANGO_API_URL || DEFAULT_API_BASE).replace(/\/?$/, '/')
  const url = new URL(path.replace(/^\//, ''), base)
  for (const [key, value] of Object.entries(params)) {
    if (value) url.searchParams.set(key, value)
  }

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

/** Follow DRF pagination if it is ever enabled, so no rows are lost. */
async function fetchAll(path, apiToken, params) {
  let data = await djangoFetch(path, apiToken, params)
  if (Array.isArray(data)) return data
  const items = [...(data?.results ?? [])]
  while (data?.next) {
    const next = new URL(data.next)
    data = await djangoFetch(next.pathname.replace(/^.*\/api\//, ''), apiToken, Object.fromEntries(next.searchParams))
    items.push(...(data?.results ?? []))
  }
  return items
}

// Period filtering happens in the API, in the requesting user's time zone,
// so a report covers exactly the calendar days the user chose.
function period(dateFrom, dateTo, tz) {
  return { start_date: dateFrom, end_date: dateTo, tz }
}

const fetchAlerts = (apiToken, dateFrom, dateTo, tz) =>
  fetchAll('alerts/', apiToken, period(dateFrom, dateTo, tz))
const fetchZones = (apiToken) => fetchAll('v1/zones/', apiToken)
const fetchWorkers = (apiToken) => fetchAll('workers/', apiToken)
const fetchActivityLogs = (apiToken, dateFrom, dateTo, tz) =>
  fetchAll('v1/activity/', apiToken, period(dateFrom, dateTo, tz))

module.exports = { fetchAlerts, fetchZones, fetchWorkers, fetchActivityLogs }
