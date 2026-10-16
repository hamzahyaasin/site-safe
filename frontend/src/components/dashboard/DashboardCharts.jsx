import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import Card, { CardContent, CardDescription, CardHeader, CardTitle } from '../ui/Card.jsx'
import Skeleton from '../ui/Skeleton.jsx'
import { shortDayLabel } from '../../lib/utils.js'

const chartTooltipStyle = {
  background: '#1a1d27',
  border: '1px solid #2a2f3d',
  borderRadius: 6,
  fontSize: 12,
}

const axisTick = { fill: '#71717a', fontSize: 11 }

/** Incident charts drawn from stored alerts only (see /dashboard/stats/).
 * Simulated alerts are shown as their own series so a demo is never
 * mistaken for real observations. */
export default function DashboardCharts({ stats, loading }) {
  if (loading) {
    return (
      <section className="col-span-12 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Skeleton className="h-72 w-full" />
        <Skeleton className="h-72 w-full" />
      </section>
    )
  }

  const hourly = (stats?.hourly_today ?? []).map((h) => ({
    hour: `${String(h.hour).padStart(2, '0')}:00`,
    observed: h.count - h.simulated,
    simulated: h.simulated,
  }))
  const daily = (stats?.daily_7d ?? []).map((d) => ({
    day: shortDayLabel(d.date),
    resolved: d.resolved,
    open: d.total - d.resolved,
  }))
  const hasToday = hourly.some((h) => h.observed + h.simulated > 0)
  const hasWeek = daily.some((d) => d.resolved + d.open > 0)

  return (
    <section className="col-span-12 grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Alerts by Hour</CardTitle>
          <CardDescription>Today, {stats?.timezone ?? 'local time'}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative h-64">
            {!hasToday ? <NoData text="No alerts recorded today" /> : null}
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hourly} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid stroke="#2a2f3d" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="hour" tick={axisTick} axisLine={{ stroke: '#2a2f3d' }} tickLine={false} />
                <YAxis allowDecimals={false} tick={axisTick} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={chartTooltipStyle}
                  labelStyle={{ color: '#a1a1aa' }}
                  cursor={{ fill: 'rgba(245, 158, 11, 0.06)' }}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: '#a1a1aa' }} />
                <Bar dataKey="observed" name="Observed" stackId="a" fill="#f59e0b" fillOpacity={0.85} maxBarSize={40} />
                <Bar dataKey="simulated" name="Simulated" stackId="a" fill="#71717a" radius={[4, 4, 0, 0]} maxBarSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Alerts by Day</CardTitle>
          <CardDescription>Last 7 days, by current resolution status</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative h-64">
            {!hasWeek ? <NoData text="No alerts recorded in the last 7 days" /> : null}
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={daily} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid stroke="#2a2f3d" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="day" tick={axisTick} axisLine={{ stroke: '#2a2f3d' }} tickLine={false} />
                <YAxis allowDecimals={false} tick={axisTick} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={chartTooltipStyle}
                  labelStyle={{ color: '#a1a1aa' }}
                  cursor={{ fill: 'rgba(34, 197, 94, 0.06)' }}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: '#a1a1aa' }} />
                <Bar dataKey="resolved" name="Resolved" stackId="d" fill="#22c55e" fillOpacity={0.8} maxBarSize={40} />
                <Bar dataKey="open" name="Open" stackId="d" fill="#ef4444" fillOpacity={0.8} radius={[4, 4, 0, 0]} maxBarSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}

function NoData({ text }) {
  return (
    <p className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center text-sm text-zinc-500">
      {text}
    </p>
  )
}
