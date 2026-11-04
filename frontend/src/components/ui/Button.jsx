import { cn } from '../../lib/utils.js'

const variants = {
  primary:
    'bg-amber-500 text-zinc-950 shadow-sm shadow-amber-950/40 hover:bg-amber-400 active:bg-amber-500 border border-amber-400/60',
  secondary:
    'bg-zinc-800/80 text-zinc-100 hover:bg-zinc-700/80 border border-zinc-700 hover:border-zinc-600',
  ghost: 'bg-transparent text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100 border border-transparent',
  // Row-level destructive actions: quiet until hovered, so a table of rows
  // is not a column of red buttons.
  danger:
    'bg-transparent text-red-400 hover:bg-red-500/10 hover:text-red-300 border border-transparent hover:border-red-500/30',
  // Confirming a destructive action (dialogs).
  destructive: 'bg-red-600 text-white hover:bg-red-500 border border-red-500/60 shadow-sm shadow-red-950/40',
  success: 'bg-emerald-600 text-white hover:bg-emerald-500 border border-emerald-500/60',
}

const sizes = {
  xs: 'h-7 px-2 text-xs gap-1',
  sm: 'h-8 px-3 text-xs gap-1.5',
  md: 'h-9 px-3.5 text-sm gap-2',
  lg: 'h-10 px-4 text-sm gap-2',
  icon: 'h-8 w-8 p-0',
}

export default function Button({
  variant = 'secondary',
  size = 'md',
  loading = false,
  disabled,
  className,
  children,
  ...props
}) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        'inline-flex shrink-0 select-none items-center justify-center whitespace-nowrap rounded-md font-medium transition-colors',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500',
        'disabled:cursor-not-allowed disabled:opacity-50 [&_svg]:shrink-0',
        variants[variant] || variants.secondary,
        sizes[size] || sizes.md,
        className,
      )}
      {...props}
    >
      {loading ? <Spinner /> : null}
      {children}
    </button>
  )
}

export function Spinner({ className }) {
  return (
    <svg className={cn('h-3.5 w-3.5 animate-spin', className)} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}
