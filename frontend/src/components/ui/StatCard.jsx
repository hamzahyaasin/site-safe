import { Link } from 'react-router-dom'
import { Area, AreaChart, ResponsiveContainer } from 'recharts'
import { cn } from '../../lib/utils.js'

const TONES = {
  emerald: { chip: 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20', stroke: '#34d399' },
  red: { chip: 'bg-red-500/10 text-red-400 ring-red-500/20', stroke: '#f87171' },
  amber: { chip: 'bg-amber-500/10 text-amber-400 ring-amber-500/20', stroke: '#fbbf24' },
  sky: { chip: 'bg-sky-500/10 text-sky-400 ring-sky-500/20', stroke: '#38bdf8' },
}

/** One headline figure. ``to`` makes the whole card a link to the page behind the number. */
export default function StatCard({
  label,
  value,
  hint,
  deltaText,
  deltaTone = 'neutral',
  tone = 'amber',
  icon: Icon,
  to,
  sparklineData = [],
  loading,
}) {
  const colors = TONES[tone] || TONES.amber
  const gradientId = `spark-${label.replace(/\s+/g, '-').toLowerCase()}`

  if (loading) {
    return (
      <div className="flex min-h-[132px] flex-col rounded-xl border border-zinc-800 bg-[#151821] p-4">
        <div className="mb-4 h-3 w-24 animate-pulse rounded bg-zinc-800" />
        <div className="mb-3 h-8 w-16 animate-pulse rounded bg-zinc-800" />
        <div className="mt-auto h-3 w-32 animate-pulse rounded bg-zinc-800" />
      </div>
    )
  }

  const body = (
    <>
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-medium text-zinc-400">{label}</p>
        {Icon ? (
          <span className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset', colors.chip)}>
            <Icon className="h-4 w-4" />
          </span>
        ) : null}
      </div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-3xl font-semibold tracking-tight tabular-nums text-zinc-50">{value ?? '—'}</span>
        {deltaText ? (
          <span
            className={cn(
              'text-xs font-medium tabular-nums',
              deltaTone === 'good' && 'text-emerald-400',
              deltaTone === 'bad' && 'text-red-400',
              deltaTone === 'neutral' && 'text-zinc-500',
            )}
          >
            {deltaText}
          </span>
        ) : null}
      </div>
      {hint ? <p className="mt-1 text-xs text-zinc-500">{hint}</p> : null}
      {sparklineData.length > 1 && sparklineData.some((d) => d.v) ? (
        <div className="-mx-1 mt-auto h-10 pt-2" aria-hidden>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparklineData} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={colors.stroke} stopOpacity={0.25} />
                  <stop offset="100%" stopColor={colors.stroke} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke={colors.stroke}
                strokeOpacity={0.8}
                fill={`url(#${gradientId})`}
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : null}
    </>
  )

  const shell =
    'group flex min-h-[132px] flex-col rounded-xl border border-zinc-800 bg-gradient-to-b from-[#171a24] to-[#141720] p-4 shadow-sm shadow-black/20'

  return to ? (
    <Link
      to={to}
      className={cn(
        shell,
        'transition-colors hover:border-zinc-700 hover:from-[#1a1d28] focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500',
      )}
    >
      {body}
    </Link>
  ) : (
    <article className={shell}>{body}</article>
  )
}
