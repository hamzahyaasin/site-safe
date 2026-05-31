import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import Card, { CardContent, CardDescription, CardHeader, CardTitle } from '../ui/Card.jsx'
import Skeleton from '../ui/Skeleton.jsx'

const ALERT_TYPE_ORDER = ['PPE_VIOLATION', 'SOS', 'ZONE_BREACH', 'INACTIVITY']

const ALERT_TYPE_COLORS = {
  PPE_VIOLATION: '#f59e0b',
  SOS: '#ef4444',
  ZONE_BREACH: '#8b5cf6',
  INACTIVITY: '#3b82f6',
}

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

function alertsByTypeChartData(stats) {
  const map = stats?.alerts_by_type || {}
  return ALERT_TYPE_ORDER.map((type) => {
    let count = 0
    if (Array.isArray(map)) {
      const row = map.find((r) => (r.name ?? r.type) === type)
      count = Number(row?.count ?? 0)
    } else {
      count = Number(map[type] ?? 0)
    }
    return {
      type,
      label: type.replace(/_/g, ' '),
      count,
      fill: ALERT_TYPE_COLORS[type],
    }
  })
}

export default function DashboardCharts({ stats, loading }) {
  const typeData = alertsByTypeChartData(stats)

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
          <CardTitle>Alerts by Type</CardTitle>
          <CardDescription>Unresolved counts by category</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={typeData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid stroke="#2a2f3d" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: '#71717a', fontSize: 10 }}
                  axisLine={{ stroke: '#2a2f3d' }}
                  tickLine={false}
                  interval={0}
                  angle={-20}
                  textAnchor="end"
                  height={56}
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
                  cursor={{ fill: 'rgba(255, 255, 255, 0.04)' }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={48}>
                  {typeData.map((entry) => (
                    <Cell key={entry.type} fill={entry.fill} fillOpacity={0.9} />
                  ))}
                </Bar>
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
