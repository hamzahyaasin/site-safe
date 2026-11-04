import StatCard from '../ui/StatCard.jsx'
import { formatMinutes } from '../../lib/utils.js'
import { IconActivity, IconAlertTriangle, IconClock, IconUsers } from '../ui/icons.jsx'

/** Every figure here comes from /dashboard/stats/; nothing is estimated. */
export default function KpiStrip({ stats, loading }) {
  const daily = stats?.daily_7d ?? []
  const today = stats?.total_alerts_today
  const yesterday = stats?.alerts_yesterday
  let todayDelta = null
  if (stats) {
    const diff = today - yesterday
    todayDelta = {
      text: diff === 0 ? 'same as yesterday' : `${diff > 0 ? '+' : ''}${diff} vs yesterday`,
      tone: diff > 0 ? 'bad' : diff < 0 ? 'good' : 'neutral',
    }
  }

  const cards = [
    {
      label: 'Workers On Site',
      value: stats?.workers_on_site,
      hint: stats
        ? `of ${stats.active_workers} active · ${stats.workers_on_site_by_camera} seen by camera, ${stats.workers_on_site_by_vest} by vest`
        : null,
      tone: 'emerald',
      icon: IconUsers,
      to: '/workers',
    },
    {
      label: 'Open Alerts',
      value: stats?.unresolved_alerts,
      hint: stats ? `${stats.critical_alerts} critical` : null,
      tone: 'red',
      icon: IconAlertTriangle,
      to: '/incidents?status=open',
    },
    {
      label: 'Alerts Today',
      value: today,
      deltaText: todayDelta?.text,
      deltaTone: todayDelta?.tone,
      hint: stats?.simulated_alerts_today ? `incl. ${stats.simulated_alerts_today} simulated` : null,
      tone: 'amber',
      icon: IconActivity,
      to: '/incidents',
      sparkline: daily.map((d) => ({ v: d.total })),
    },
    {
      label: 'Mean Time To Resolve',
      value: stats ? (formatMinutes(stats.mean_resolution_minutes_7d) ?? '—') : null,
      hint: stats
        ? stats.resolved_7d
          ? `${stats.resolved_7d} alerts resolved in the last 7 days`
          : 'No alerts resolved in the last 7 days'
        : null,
      tone: 'sky',
      icon: IconClock,
    },
  ]

  return (
    <section className="col-span-12 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <StatCard
          key={card.label}
          label={card.label}
          value={card.value}
          hint={card.hint}
          deltaText={card.deltaText}
          deltaTone={card.deltaTone}
          tone={card.tone}
          icon={card.icon}
          to={card.to}
          sparklineData={card.sparkline}
          loading={loading}
        />
      ))}
    </section>
  )
}
