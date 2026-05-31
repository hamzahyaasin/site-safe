import StatCard from '../ui/StatCard.jsx'
import { sparklineFromValue } from '../../lib/utils.js'

function countByType(stats, type) {
  const map = stats?.alerts_by_type
  if (!map) return null
  if (Array.isArray(map)) {
    const row = map.find((r) => (r.name ?? r.type) === type)
    return row ? Number(row.count ?? 0) : 0
  }
  return Number(map[type] ?? 0)
}

export default function KpiStrip({ stats, loading }) {
  const zoneBreaches = countByType(stats, 'ZONE_BREACH')
  const inactivityAlerts = countByType(stats, 'INACTIVITY')

  const cards = [
    {
      label: 'Active Workers',
      value: stats?.active_workers,
      delta: stats ? 2 : null,
      borderColor: 'border-l-emerald-500',
      sparkline: sparklineFromValue(stats?.active_workers),
      sparklineTrend: 'positive',
    },
    {
      label: 'Open Alerts',
      value: stats?.unresolved_alerts,
      delta: stats ? -5 : null,
      borderColor: 'border-l-red-500',
      sparkline: sparklineFromValue(stats?.unresolved_alerts),
      sparklineTrend: 'negative',
    },
    {
      label: 'Zone Breaches',
      value: zoneBreaches,
      delta: stats && zoneBreaches !== null ? (zoneBreaches > 0 ? zoneBreaches : -1) : null,
      borderColor: 'border-l-violet-500',
      sparkline: sparklineFromValue(zoneBreaches),
      sparklineTrend: 'negative',
    },
    {
      label: 'Inactivity',
      value: inactivityAlerts,
      delta: stats && inactivityAlerts !== null ? (inactivityAlerts > 0 ? inactivityAlerts : -1) : null,
      borderColor: 'border-l-blue-500',
      sparkline: sparklineFromValue(inactivityAlerts),
      sparklineTrend: 'negative',
    },
  ]

  return (
    <section className="col-span-12 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <StatCard
          key={card.label}
          label={card.label}
          value={card.value}
          delta={card.delta}
          borderColor={card.borderColor}
          sparklineData={card.sparkline}
          sparklineTrend={card.sparklineTrend}
          loading={loading}
        />
      ))}
    </section>
  )
}
