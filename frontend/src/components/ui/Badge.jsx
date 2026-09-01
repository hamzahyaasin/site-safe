import { cn } from '../../lib/utils.js'

const variants = {
  neutral: 'bg-zinc-800 text-zinc-300 border-zinc-700',
  primary: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  critical: 'bg-red-500/15 text-red-400 border-red-500/30',
  high: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
  low: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  success: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  offline: 'bg-zinc-700/50 text-zinc-400 border-zinc-600',
  active: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  atRisk: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
}

export default function Badge({ variant = 'neutral', className, children, ...props }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide',
        variants[variant] || variants.neutral,
        className,
      )}
      {...props}
    >
      {children}
    </span>
  )
}
