import { useId } from 'react'
import { cn } from '../../lib/utils.js'

const FIELD =
  'w-full rounded-md border border-zinc-700 bg-zinc-900/80 px-3 text-sm text-zinc-100 shadow-inner shadow-black/10 transition-colors placeholder:text-zinc-500 hover:border-zinc-600 focus:border-amber-500/60 focus:outline-none focus:ring-2 focus:ring-amber-500/20 disabled:cursor-not-allowed disabled:opacity-60 read-only:bg-zinc-900/40 read-only:text-zinc-300'

function FieldLabel({ children }) {
  return children ? <span className="text-xs font-medium text-zinc-300">{children}</span> : null
}

function FieldHint({ children }) {
  return children ? <span className="text-[11px] leading-snug text-zinc-500">{children}</span> : null
}

export default function Input({ label, hint, className, inputClassName, id, ...props }) {
  const autoId = useId()
  const inputId = id || autoId
  return (
    <label className={cn('flex flex-col gap-1.5', className)} htmlFor={inputId}>
      <FieldLabel>{label}</FieldLabel>
      <input id={inputId} className={cn(FIELD, 'h-9', inputClassName)} {...props} />
      <FieldHint>{hint}</FieldHint>
    </label>
  )
}

export function Select({ label, hint, className, selectClassName, children, id, ...props }) {
  const autoId = useId()
  const selectId = id || autoId
  return (
    <label className={cn('flex flex-col gap-1.5', className)} htmlFor={selectId}>
      <FieldLabel>{label}</FieldLabel>
      <select id={selectId} className={cn(FIELD, 'h-9 pr-8', selectClassName)} {...props}>
        {children}
      </select>
      <FieldHint>{hint}</FieldHint>
    </label>
  )
}

export function Textarea({ label, hint, className, rows = 3, id, ...props }) {
  const autoId = useId()
  const fieldId = id || autoId
  return (
    <label className={cn('flex flex-col gap-1.5', className)} htmlFor={fieldId}>
      <FieldLabel>{label}</FieldLabel>
      <textarea id={fieldId} rows={rows} className={cn(FIELD, 'py-2')} {...props} />
      <FieldHint>{hint}</FieldHint>
    </label>
  )
}

/** Checkbox with a label and an optional explanation underneath. */
export function Checkbox({ label, hint, className, ...props }) {
  return (
    <label className={cn('flex cursor-pointer items-start gap-2.5 text-sm text-zinc-200', className)}>
      <input
        type="checkbox"
        className="mt-0.5 h-4 w-4 shrink-0 cursor-pointer rounded border-zinc-600 bg-zinc-900"
        {...props}
      />
      <span className="flex flex-col gap-0.5">
        <span>{label}</span>
        <FieldHint>{hint}</FieldHint>
      </span>
    </label>
  )
}
