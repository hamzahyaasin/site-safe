function formatDate(iso, tz) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  return d.toLocaleString('en-GB', {
    timeZone: tz || 'UTC',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const ACRONYMS = { ppe: 'PPE', sos: 'SOS', ai: 'AI' }

function formatLabel(value) {
  const words = String(value ?? '—').replace(/_/g, ' ').toLowerCase().split(' ')
  const out = words.map((w) => ACRONYMS[w] ?? w).join(' ')
  return out.charAt(0).toUpperCase() + out.slice(1)
}

function formatDuration(minutes) {
  if (minutes === null || minutes === undefined) return '—'
  if (minutes < 1) return '< 1 min'
  if (minutes < 60) return `${Math.round(minutes)} min`
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  if (h >= 48) return `${(minutes / 1440).toFixed(1)} days`
  return m ? `${h} h ${m} min` : `${h} h`
}

function plural(n, word) {
  return `${n} ${word}${n === 1 ? '' : 's'}`
}

/** "was" or "were" to agree with a count. */
function was(n) {
  return n === 1 ? 'was' : 'were'
}

module.exports = { formatDate, formatDuration, formatLabel, plural, was }
