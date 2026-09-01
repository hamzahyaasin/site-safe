import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'

export function useDashboardStats() {
  const { api } = useAuth()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchStats = useCallback(async () => {
    try {
      const { data } = await api.get('dashboard/stats/')
      setStats(data)
    } finally {
      setLoading(false)
    }
  }, [api])

  useEffect(() => {
    fetchStats()
    const t = window.setInterval(fetchStats, 15000)
    return () => window.clearInterval(t)
  }, [fetchStats])

  return { stats, loading, fetchStats }
}
