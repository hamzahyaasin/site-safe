import { cn } from '../../lib/utils.js'

const variants = {
  neutral: 'bg-zinc-800/80 text-zinc-300 ring-zinc-600/40',
  primary: 'bg-amber-500/10 text-amber-300 ring-amber-500/30',
  critical: 'bg-red-500/10 text-red-300 ring-red-500/30',
  high: 'bg-orange-500/10 text-orange-300 ring-orange-500/30',
  medium: 'bg-yellow-500/10 text-yellow-300 ring-yellow-500/30',
  low: 'bg-sky-500/10 text-sky-300 ring-sky-500/30',
  success: 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/30',
  offline: 'bg-zinc-800/60 text-zinc-400 ring-zinc-600/40',
  active: 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/30',
  atRisk: 'bg-amber-500/10 text-amber-300 ring-amber-500/30',
}

const dots = {
  critical: 'bg-red-400',
  high: 'bg-orange-400',
  medium: 'bg-yellow-400',
  low: 'bg-sky-400',
  success: 'bg-emerald-400',
  active: 'bg-emerald-400',
  offline: 'bg-zinc-500',
  atRisk: 'bg-amber-400',
  primary: 'bg-amber-400',
  neutral: 'bg-zinc-400',
}

/** Status label. ``dot`` adds a coloured dot before the text. */
export default function Badge({ variant = 'neutral', dot = false, className, children, ...props }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-md px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset',
        variants[variant] || variants.neutral,
        className,
      )}
      {...props}
    >
      {dot ? <span className={cn('h-1.5 w-1.5 rounded-full', dots[variant] || dots.neutral)} aria-hidden /> : null}
      {children}
    </span>
  )
}
