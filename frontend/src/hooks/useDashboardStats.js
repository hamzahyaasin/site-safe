import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { useWebSocketContext } from './useWebSocketContext.js'
import { browserTimeZone } from '../lib/utils.js'

const POLL_MS = 60000
const REFRESH_EVENTS = new Set([
  'alert_created',
  'alert_resolved',
  'alert_updated',
  'vest_updated',
  'worker_status_update',
  'resync',
])

export function useDashboardStats() {
  const { api } = useAuth()
  const { subscribe } = useWebSocketContext()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const debounceRef = useRef(null)

  const fetchStats = useCallback(async () => {
    try {
      const { data } = await api.get('dashboard/stats/', { params: { tz: browserTimeZone() } })
      setStats(data)
    } finally {
      setLoading(false)
    }
  }, [api])

  useEffect(() => {
    const first = window.setTimeout(fetchStats, 0)
    const t = window.setInterval(fetchStats, POLL_MS)
    return () => {
      window.clearTimeout(first)
      window.clearInterval(t)
    }
  }, [fetchStats])

  // Live events change the figures; coalesce bursts into one refetch.
  useEffect(() => {
    const unsubscribe = subscribe((event) => {
      if (!REFRESH_EVENTS.has(event)) return
      window.clearTimeout(debounceRef.current)
      debounceRef.current = window.setTimeout(fetchStats, 500)
    })
    return () => {
      unsubscribe()
      window.clearTimeout(debounceRef.current)
    }
  }, [subscribe, fetchStats])

  return { stats, loading, fetchStats }
}
