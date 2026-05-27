import { cn } from '../../lib/utils.js'

export default function Skeleton({ className, ...props }) {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-zinc-800/80', className)}
      aria-hidden="true"
      {...props}
    />
  )
}

export function SkeletonStatCard() {
  return (
    <div className="rounded-lg border border-zinc-800 bg-[#151821] p-4">
      <Skeleton className="mb-3 h-3 w-24" />
      <Skeleton className="mb-2 h-8 w-16" />
      <Skeleton className="h-8 w-full" />
    </div>
  )
}

export function SkeletonTable({ rows = 5 }) {
  return (
    <div className="space-y-2">
      <Skeleton className="h-9 w-full" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" style={{ opacity: 1 - i * 0.08 }} />
      ))}
    </div>
  )
}
