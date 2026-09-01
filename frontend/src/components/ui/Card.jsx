import { cn } from '../../lib/utils.js'

export default function Card({ className, children, ...props }) {
  return (
    <div
      className={cn(
        'rounded-lg border border-zinc-800 bg-[#151821] text-zinc-100',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ className, children, ...props }) {
  return (
    <div className={cn('border-b border-zinc-800 px-4 py-3', className)} {...props}>
      {children}
    </div>
  )
}

export function CardTitle({ className, children, ...props }) {
  return (
    <h3 className={cn('text-sm font-semibold text-zinc-100', className)} {...props}>
      {children}
    </h3>
  )
}

export function CardDescription({ className, children, ...props }) {
  return (
    <p className={cn('mt-0.5 text-xs text-zinc-500', className)} {...props}>
      {children}
    </p>
  )
}

export function CardContent({ className, children, ...props }) {
  return (
    <div className={cn('p-4', className)} {...props}>
      {children}
    </div>
  )
}
