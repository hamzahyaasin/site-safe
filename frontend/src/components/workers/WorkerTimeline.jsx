import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../../context/AuthContext.jsx'
import Drawer from '../ui/Drawer.jsx'
import Input from '../ui/Input.jsx'
import { browserTimeZone, formatMinutes } from '../../lib/utils.js'

const ZONE_COLORS = ['#3b82f6', '#a855f7', '#14b8a6', '#f43f5e', '#84cc16', '#eab308']

function todayLocal() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function hhmm(iso) {
  return iso ? new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }) : '—'
}

/** Position of an interval within the day as left/width percentages. */
function span(day, interval) {
  const start = new Date(`${day}T00:00:00`).getTime()
  const dayMs = 24 * 3600 * 1000
  const a = Math.max(0, new Date(interval.start).getTime() - start)
  const b = Math.min(dayMs, new Date(interval.end).getTime() - start)
  return { left: `${(a / dayMs) * 100}%`, width: `${Math.max(0.3, ((b - a) / dayMs) * 100)}%` }
}

function Track({ label, day, items, color, colorFor, titleFor }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-16 shrink-0 text-[11px] text-zinc-500">{label}</span>
      <div className="relative h-5 flex-1 rounded bg-zinc-800/60">
        {items.map((it, i) => (
          <div
            key={i}
            title={titleFor(it)}
            className="absolute top-0 h-5 rounded-sm"
            style={{ ...span(day, it), background: colorFor ? colorFor(it) : color, opacity: it.open ? 0.6 : 0.9 }}
          />
        ))}
      </div>
    </div>
  )
}

/**
 * A worker's day: on-site sessions, idle periods and zone visits, built
 * from vest reports and QR sightings. Workers with neither have no timeline,
 * which is shown as "no evidence", never as absence.
 */
export default function WorkerTimeline({ worker, onClose }) {
  const { api } = useAuth()
  const [day, setDay] = useState(todayLocal)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    if (!worker) return
    try {
      const { data: t } = await api.get('v1/activity/timeline/', {
        params: { worker_id: worker.id, date: day, tz: browserTimeZone() },
      })
      setData(t)
      setError('')
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load timeline')
    }
  }, [api, worker, day])

  useEffect(() => {
    const t = window.setTimeout(load, 0)
    return () => window.clearTimeout(t)
  }, [load])

  const zoneNames = [...new Set((data?.zones ?? []).map((z) => z.zone_name))]
  const zoneColor = (z) => ZONE_COLORS[zoneNames.indexOf(z.zone_name) % ZONE_COLORS.length]

  return (
    <Drawer open={Boolean(worker)} onClose={onClose} title={worker ? `${worker.name}: activity` : ''} description="From vest reports and QR badge sightings">
      <div className="space-y-5">
        <Input label="Day" type="date" value={day} max={todayLocal()} onChange={(e) => setDay(e.target.value)} />
        {error ? <p className="text-xs text-red-400">{error}</p> : null}
        {data && !data.has_activity ? (
          <p className="rounded-md border border-zinc-800 p-3 text-sm text-zinc-400">
            No vest report or badge sighting for this worker on this day. Their presence is unknown; it is not recorded as absence.
          </p>
        ) : null}
        {data && data.has_activity ? (
          <>
            <div className="grid grid-cols-3 gap-2 text-center">
              <Stat label="On site" value={formatMinutes(data.on_site_minutes) ?? '0 min'} />
              <Stat label="Idle" value={formatMinutes(data.idle_minutes) ?? '0 min'} />
              <Stat label="First in" value={hhmm(data.first_check_in)} />
            </div>
            <div className="space-y-1.5">
              <Track label="On site" day={day} items={data.sessions} color="#22c55e" titleFor={(s) => `${hhmm(s.start)}–${s.open ? 'now' : hhmm(s.end)}`} />
              <Track label="Idle" day={day} items={data.idle} color="#f59e0b" titleFor={(s) => `Idle ${hhmm(s.start)}–${s.open ? 'now' : hhmm(s.end)}`} />
              <Track label="Zones" day={day} items={data.zones} colorFor={zoneColor} titleFor={(z) => `${z.zone_name}: ${hhmm(z.start)}–${z.open ? 'now' : hhmm(z.end)}`} />
              <div className="ml-[72px] flex justify-between text-[10px] text-zinc-600">
                {['00', '06', '12', '18', '24'].map((h) => (
                  <span key={h}>{h}:00</span>
                ))}
              </div>
            </div>
            {zoneNames.length ? (
              <div className="flex flex-wrap gap-3 text-[11px] text-zinc-400">
                {zoneNames.map((name) => (
                  <span key={name} className="flex items-center gap-1">
                    <span className="h-2 w-2 rounded-sm" style={{ background: zoneColor({ zone_name: name }) }} />
                    {name} · {formatMinutes(data.zone_minutes[name]) ?? '0 min'}
                  </span>
                ))}
              </div>
            ) : null}
            <ul className="space-y-1 text-xs text-zinc-300">
              {data.sessions.map((s, i) => (
                <li key={`s${i}`}>
                  On site {hhmm(s.start)} – {s.open ? <em className="text-emerald-400">still here</em> : hhmm(s.end)}
                </li>
              ))}
              {data.idle.map((s, i) => (
                <li key={`i${i}`} className="text-amber-300/90">
                  Idle {hhmm(s.start)} – {s.open ? 'ongoing' : hhmm(s.end)}
                </li>
              ))}
            </ul>
            <p className="text-[11px] text-zinc-600">
              Evidence: {data.evidence_sources.join(', ') || '—'} · times in {data.timezone}. A session ends{' '}
              automatically when the worker has not been seen for a while, at the time they were last seen.
            </p>
          </>
        ) : null}
      </div>
    </Drawer>
  )
}

function Stat({ label, value }) {
  return (
    <div className="rounded-md border border-zinc-800 p-2">
      <p className="text-[10px] uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="text-sm font-semibold text-zinc-100">{value}</p>
    </div>
  )
}
