import { Area, AreaChart, ResponsiveContainer } from 'recharts'
import { cn } from '../../lib/utils.js'

const SPARKLINE_POSITIVE = {
  stroke: 'rgba(239, 159, 39, 0.8)',
  fillStart: 'rgba(239, 159, 39, 0.2)',
  fillEnd: 'rgba(239, 159, 39, 0)',
}

const SPARKLINE_NEGATIVE = {
  stroke: 'rgba(239, 68, 68, 0.7)',
  fillStart: 'rgba(239, 68, 68, 0.2)',
  fillEnd: 'rgba(239, 68, 68, 0)',
}

export default function StatCard({
  label,
  value,
  delta,
  deltaLabel = 'vs yesterday',
  borderColor = 'border-l-amber-500',
  sparklineData = [],
  sparklineTrend = 'positive',
  loading,
}) {
  const gradientId = `spark-${label.replace(/\s+/g, '-').toLowerCase()}`
  const colors = sparklineTrend === 'negative' ? SPARKLINE_NEGATIVE : SPARKLINE_POSITIVE

  if (loading) {
    return (
      <div className="flex min-h-[140px] flex-col rounded-lg border border-zinc-800 border-l-4 border-l-zinc-700 bg-[#151821] p-4">
        <div className="mb-2 h-3 w-24 animate-pulse rounded bg-zinc-800" />
        <div className="mb-3 h-8 w-16 animate-pulse rounded bg-zinc-800" />
        <div className="mt-auto h-14 animate-pulse rounded bg-zinc-800" />
      </div>
    )
  }

  const deltaNum = Number(delta)
  const deltaPositive = deltaNum >= 0

  return (
    <article
      className={cn(
        'flex min-h-[140px] flex-col rounded-lg border border-zinc-800 border-l-4 bg-[#151821] p-4',
        borderColor,
      )}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</p>
      <div className="mt-1 flex items-end justify-between gap-2">
        <span className="text-2xl font-semibold tabular-nums text-zinc-100">
          {value ?? '—'}
        </span>
        {delta !== undefined && delta !== null ? (
          <span
            className={cn(
              'text-xs font-medium tabular-nums',
              deltaPositive ? 'text-emerald-400' : 'text-red-400',
            )}
          >
            {deltaPositive ? '+' : ''}
            {delta}% {deltaLabel}
          </span>
        ) : null}
      </div>
      {sparklineData.length > 0 ? (
        <div className="mt-auto h-[40%] min-h-[52px] w-full pt-3">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparklineData} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={colors.fillStart} />
                  <stop offset="100%" stopColor={colors.fillEnd} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke={colors.stroke}
                fill={`url(#${gradientId})`}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : null}
    </article>
  )
}
