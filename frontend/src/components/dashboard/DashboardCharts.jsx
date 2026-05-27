import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import Card, { CardContent, CardDescription, CardHeader, CardTitle } from '../ui/Card.jsx'
import Skeleton from '../ui/Skeleton.jsx'

const HOURLY_DATA = [
  { hour: '06:00', count: 1 },
  { hour: '08:00', count: 3 },
  { hour: '10:00', count: 5 },
  { hour: '12:00', count: 2 },
  { hour: '14:00', count: 7 },
  { hour: '16:00', count: 4 },
  { hour: '18:00', count: 1 },
]

const COMPLIANCE_DATA = [
  { day: 'Mon', rate: 92 },
  { day: 'Tue', rate: 88 },
  { day: 'Wed', rate: 91 },
  { day: 'Thu', rate: 85 },
  { day: 'Fri', rate: 90 },
  { day: 'Sat', rate: 94 },
  { day: 'Sun', rate: 96 },
]

const chartTooltipStyle = {
  background: '#1a1d27',
  border: '1px solid #2a2f3d',
  borderRadius: 6,
  fontSize: 12,
}

export default function DashboardCharts({ stats, loading }) {
  const hourlyData = stats?.total_alerts_today
    ? HOURLY_DATA.map((d, i) => ({
        ...d,
        count: Math.max(0, Math.round(d.count * (stats.total_alerts_today / 23) + (i % 2))),
      }))
    : HOURLY_DATA

  if (loading) {
    return (
      <section className="col-span-12 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Skeleton className="h-72 w-full" />
        <Skeleton className="h-72 w-full" />
      </section>
    )
  }

  return (
    <section className="col-span-12 grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Hourly Violations</CardTitle>
          <CardDescription>Frequency by hour — today</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hourlyData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid stroke="#2a2f3d" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="hour"
                  tick={{ fill: '#71717a', fontSize: 11 }}
                  axisLine={{ stroke: '#2a2f3d' }}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: '#71717a', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={chartTooltipStyle}
                  labelStyle={{ color: '#a1a1aa' }}
                  cursor={{ fill: 'rgba(245, 158, 11, 0.06)' }}
                />
                <Bar dataKey="count" fill="#f59e0b" fillOpacity={0.85} radius={[4, 4, 0, 0]} maxBarSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Compliance Rate</CardTitle>
          <CardDescription>7-day trend (%)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={COMPLIANCE_DATA} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid stroke="#2a2f3d" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="day"
                  tick={{ fill: '#71717a', fontSize: 11 }}
                  axisLine={{ stroke: '#2a2f3d' }}
                  tickLine={false}
                />
                <YAxis
                  domain={[70, 100]}
                  tick={{ fill: '#71717a', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={chartTooltipStyle}
                  labelStyle={{ color: '#a1a1aa' }}
                  formatter={(v) => [`${v}%`, 'Compliance']}
                />
                <Area
                  type="monotone"
                  dataKey="rate"
                  stroke="#22c55e"
                  fill="#22c55e"
                  fillOpacity={0.12}
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}
