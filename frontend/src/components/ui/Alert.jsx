import { cn } from '../../lib/utils.js'

const tones = {
  error: 'border-red-500/30 bg-red-500/10 text-red-300',
  warning: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
  success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  info: 'border-sky-500/30 bg-sky-500/10 text-sky-200',
}

/** Inline message banner for form errors, success notes and page-level warnings. */
export default function Alert({ tone = 'error', className, children }) {
  return (
    <p
      role={tone === 'error' ? 'alert' : 'status'}
      className={cn('rounded-md border px-3 py-2 text-xs leading-relaxed', tones[tone], className)}
    >
      {children}
    </p>
  )
}
