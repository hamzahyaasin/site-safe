import { cn } from '../../lib/utils.js'

/** Title, one-line description and the page's primary actions, laid out the same on every page. */
export default function PageHeader({ title, description, actions, className }) {
  return (
    <header className={cn('flex flex-wrap items-start justify-between gap-x-6 gap-y-3', className)}>
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-50">{title}</h1>
        {description ? <p className="mt-1 max-w-3xl text-sm text-zinc-400">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  )
}
