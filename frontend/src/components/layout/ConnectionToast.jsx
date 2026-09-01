import { useEffect } from 'react'
import { cn } from '../../lib/utils.js'
import { useWebSocket } from '../../hooks/useWebSocket.js'

export default function ConnectionToast() {
  const { connectionToast, dismissConnectionToast, status } = useWebSocket()

  useEffect(() => {
    if (!connectionToast || status === 'live') return undefined
    const t = window.setTimeout(dismissConnectionToast, 6000)
    return () => window.clearTimeout(t)
  }, [connectionToast, status, dismissConnectionToast])

  if (!connectionToast || status === 'live') return null

  return (
    <div
      role="status"
      className={cn(
        'fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-lg border px-4 py-2.5 text-sm shadow-lg backdrop-blur-sm',
        connectionToast.type === 'error'
          ? 'border-red-500/40 bg-red-500/10 text-red-300'
          : 'border-amber-500/40 bg-amber-500/10 text-amber-200',
      )}
    >
      {connectionToast.message}
    </div>
  )
}
