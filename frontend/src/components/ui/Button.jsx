import { cn } from '../../lib/utils.js'

const variants = {
  primary:
    'bg-amber-500 text-zinc-950 hover:bg-amber-400 border border-amber-500 disabled:opacity-50',
  secondary:
    'bg-zinc-800 text-zinc-200 hover:bg-zinc-700 border border-zinc-600 disabled:opacity-50',
  ghost: 'bg-transparent text-zinc-300 hover:bg-zinc-800 border border-transparent disabled:opacity-50',
  destructive:
    'bg-red-600/90 text-white hover:bg-red-500 border border-red-600 disabled:opacity-50',
  success:
    'bg-emerald-600/90 text-white hover:bg-emerald-500 border border-emerald-600 disabled:opacity-50',
}

const sizes = {
  sm: 'h-7 px-2.5 text-xs gap-1',
  md: 'h-9 px-3.5 text-sm gap-1.5',
  lg: 'h-10 px-4 text-sm gap-2',
}

export default function Button({
  variant = 'secondary',
  size = 'md',
  className,
  children,
  ...props
}) {
  return (
    <button
      type="button"
      className={cn(
        'inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500 disabled:cursor-not-allowed',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}
