import { cn } from '../../lib/utils.js'

/** A toggleable filter. Selected chips show a check so the state is not carried by colour alone. */
export default function FilterChip({ selected, onClick, children, className }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={cn(
        'inline-flex h-7 items-center gap-1 rounded-full border px-2.5 text-xs font-medium transition-colors',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500',
        selected
          ? 'border-amber-500/50 bg-amber-500/15 text-amber-300'
          : 'border-zinc-700 bg-zinc-900/40 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200',
        className,
      )}
    >
      {selected ? (
        <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" aria-hidden>
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ) : null}
      {children}
    </button>
  )
}

/** One-of-several choice shown as a joined row of buttons (e.g. All / Open / Resolved). */
export function SegmentedControl({ options, value, onChange, label }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-md border border-zinc-700 bg-zinc-900/60 p-0.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          role="radio"
          aria-checked={value === opt.value}
          onClick={() => onChange(opt.value)}
          className={cn(
            'h-7 rounded px-3 text-xs font-medium transition-colors',
            'focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500',
            value === opt.value ? 'bg-zinc-700 text-zinc-50 shadow-sm' : 'text-zinc-400 hover:text-zinc-200',
          )}
        >
          {opt.label}
          {opt.count !== undefined ? <span className="ml-1.5 tabular-nums text-zinc-500">{opt.count}</span> : null}
        </button>
      ))}
    </div>
  )
}
