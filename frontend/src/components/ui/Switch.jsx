import { cn } from '../../lib/utils.js'

/** On/off switch. ``label`` is read by screen readers when no visible label is next to it. */
export default function Switch({ checked, onChange, disabled, label, className }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500',
        'disabled:cursor-not-allowed disabled:opacity-50',
        checked ? 'border-amber-400/60 bg-amber-500' : 'border-zinc-600 bg-zinc-700',
        className,
      )}
    >
      <span
        aria-hidden
        className={cn(
          'pointer-events-none absolute left-0.5 h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform',
          checked ? 'translate-x-4' : 'translate-x-0',
        )}
      />
    </button>
  )
}
