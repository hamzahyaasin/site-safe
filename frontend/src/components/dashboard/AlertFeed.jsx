import { useState } from 'react'
import { Link } from 'react-router-dom'
import AlertItem from '../ui/AlertItem.jsx'
import Card, { CardContent, CardDescription, CardHeader, CardTitle } from '../ui/Card.jsx'
import Skeleton from '../ui/Skeleton.jsx'
import { IconChevronRight } from '../ui/icons.jsx'
import { apiErrorText, useFeedback } from '../../context/FeedbackContext.jsx'

export default function AlertFeed({ alerts, loading, onResolve, newAlertIds }) {
  const [resolvingId, setResolvingId] = useState(null)
  const { toast } = useFeedback()

  async function handleResolve(id) {
    setResolvingId(id)
    try {
      await onResolve(id)
      toast('Incident resolved')
    } catch (e) {
      toast(apiErrorText(e, 'Could not resolve the incident'), 'error')
    } finally {
      setResolvingId(null)
    }
  }

  return (
    <Card className="col-span-12 flex max-h-[640px] flex-col xl:col-span-4">
      <CardHeader className="flex items-start justify-between gap-3">
        <div>
          <CardTitle>Alert Feed</CardTitle>
          <CardDescription>
            {alerts.length ? `${alerts.length} open incident${alerts.length === 1 ? '' : 's'} requiring attention` : 'Live incidents requiring attention'}
          </CardDescription>
        </div>
        <Link
          to="/incidents?status=open"
          className="inline-flex shrink-0 items-center gap-0.5 rounded text-xs font-medium text-amber-400 hover:text-amber-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500"
        >
          View all
          <IconChevronRight className="h-3.5 w-3.5" />
        </Link>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col p-0">
        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div className="m-4 flex flex-col items-center justify-center rounded-lg border border-emerald-500/30 bg-emerald-500/[0.03] px-6 py-12 text-center">
            <IconShieldCheck className="mb-3 h-8 w-8 text-emerald-500/70" />
            <p className="text-sm font-medium text-zinc-200">All clear</p>
            <p className="mt-1 text-xs text-zinc-500">No active incidents on this site</p>
          </div>
        ) : (
          <div className="min-h-0 flex-1 overflow-y-auto scrollbar-thin">
            {alerts.slice(0, 50).map((alert) => (
              <AlertItem
                key={alert.id}
                alert={alert}
                onResolve={onResolve ? handleResolve : undefined}
                resolving={resolvingId === alert.id}
                isNew={newAlertIds?.has(alert.id)}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function IconShieldCheck({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <polyline points="9 12 11 14 15 10" />
    </svg>
  )
}
