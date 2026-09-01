import { cn } from '../../lib/utils.js'

export default function Input({ label, className, inputClassName, id, ...props }) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <label className={cn('flex flex-col gap-1.5', className)} htmlFor={inputId}>
      {label ? (
        <span className="text-xs font-medium text-zinc-400">{label}</span>
      ) : null}
      <input
        id={inputId}
        className={cn(
          'h-9 rounded-md border border-zinc-700 bg-zinc-900/80 px-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/30',
          inputClassName,
        )}
        {...props}
      />
    </label>
  )
}

export function Select({ label, className, selectClassName, children, id, ...props }) {
  const selectId = id || label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <label className={cn('flex flex-col gap-1.5', className)} htmlFor={selectId}>
      {label ? (
        <span className="text-xs font-medium text-zinc-400">{label}</span>
      ) : null}
      <select
        id={selectId}
        className={cn(
          'h-9 rounded-md border border-zinc-700 bg-zinc-900/80 px-3 text-sm text-zinc-100 focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/30',
          selectClassName,
        )}
        {...props}
      >
        {children}
      </select>
    </label>
  )
}
