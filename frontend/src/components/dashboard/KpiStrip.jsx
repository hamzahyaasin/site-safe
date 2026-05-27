import StatCard from '../ui/StatCard.jsx'
import { deriveComplianceRate, sparklineFromValue } from '../../lib/utils.js'

export default function KpiStrip({ stats, loading }) {
  const compliance = deriveComplianceRate(stats)

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
      label: 'Violations Today',
      value: stats?.total_alerts_today,
      delta: stats ? 8 : null,
      borderColor: 'border-l-amber-500',
      sparkline: sparklineFromValue(stats?.total_alerts_today),
      sparklineTrend: 'negative',
    },
    {
      label: 'Compliance Rate',
      value: compliance !== null ? `${compliance}%` : null,
      delta: stats ? 3 : null,
      borderColor: 'border-l-blue-500',
      sparkline: sparklineFromValue(compliance),
      sparklineTrend: 'positive',
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
