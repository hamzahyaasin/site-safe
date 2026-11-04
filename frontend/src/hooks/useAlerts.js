import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { useWebSocketContext } from './useWebSocketContext.js'
import { normalizeList } from '../lib/utils.js'

export function useAlerts(initialParams = {}) {
  const paramsKey = JSON.stringify(initialParams)
  const { api } = useAuth()
  const { subscribe } = useWebSocketContext()
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [newAlertIds, setNewAlertIds] = useState(() => new Set())

  // ``quiet`` refreshes in place (after a resolve, on resync) without
  // swapping the list for a loading skeleton.
  const fetchAlerts = useCallback(async ({ quiet = false } = {}) => {
    const params = JSON.parse(paramsKey)
    if (!quiet) setLoading(true)
    try {
      const { data } = await api.get('alerts/', { params })
      setAlerts(normalizeList(data))
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [api, paramsKey])

  useEffect(() => {
    // Initial fetch + refetch when query params change
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async data load on mount/param change
    void fetchAlerts()
  }, [fetchAlerts])

  useEffect(() => {
    const { is_resolved: resolvedFilter } = JSON.parse(paramsKey)
    const onlyOpen = String(resolvedFilter) === 'false'
    return subscribe((event, payload) => {
      if (event === 'resync') {
        void fetchAlerts({ quiet: true })
      } else if (event === 'alert_updated' || event === 'alert_resolved') {
        setAlerts((prev) => {
          if (onlyOpen && payload.is_resolved) return prev.filter((a) => a.id !== payload.id)
          return prev.map((a) => (a.id === payload.id ? payload : a))
        })
      } else if (event === 'alert_created') {
        setAlerts((prev) => {
          if (prev.some((a) => a.id === payload.id)) return prev
          return [payload, ...prev]
        })
        setNewAlertIds((prev) => new Set(prev).add(payload.id))
        window.setTimeout(() => {
          setNewAlertIds((prev) => {
            const next = new Set(prev)
            next.delete(payload.id)
            return next
          })
        }, 2600)
      }
    })
  }, [subscribe, paramsKey, fetchAlerts])

  const resolveAlert = useCallback(
    async (id) => {
      await api.post(`alerts/${id}/resolve/`)
      await fetchAlerts({ quiet: true })
    },
    [api, fetchAlerts],
  )

  return { alerts, loading, error, fetchAlerts, resolveAlert, newAlertIds }
}
