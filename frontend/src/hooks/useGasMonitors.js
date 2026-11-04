import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { useWebSocketContext } from './useWebSocketContext.js'

function normalizeList(data) {
  return Array.isArray(data) ? data : data?.results || []
}

const POLL_MS = 10000

/** Fixed gas monitors (one or more per zone), kept live from gas_monitor_* events. */
export function useGasMonitors(options = {}) {
  const { poll = true } = options
  const { api } = useAuth()
  const { subscribe } = useWebSocketContext()
  const [monitors, setMonitors] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchMonitors = useCallback(async () => {
    try {
      const { data } = await api.get('v1/gas-monitors/')
      setMonitors(normalizeList(data))
      setError(null)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load gas monitors')
      setMonitors([])
    } finally {
      setLoading(false)
    }
  }, [api])

  const createMonitor = useCallback(
    async (payload) => {
      const { data } = await api.post('v1/gas-monitors/', payload)
      await fetchMonitors()
      return data
    },
    [api, fetchMonitors],
  )

  const updateMonitor = useCallback(
    async (id, payload) => {
      const { data } = await api.patch(`v1/gas-monitors/${id}/`, payload)
      setMonitors((prev) => prev.map((m) => (m.id === id ? { ...m, ...data } : m)))
      return data
    },
    [api],
  )

  const deleteMonitor = useCallback(
    async (id) => {
      await api.delete(`v1/gas-monitors/${id}/`)
      setMonitors((prev) => prev.filter((m) => m.id !== id))
    },
    [api],
  )

  useEffect(() => {
    // Deferred so the initial load's state updates happen outside the effect body.
    const t = window.setTimeout(() => {
      fetchMonitors()
    }, 0)
    return () => window.clearTimeout(t)
  }, [fetchMonitors])

  useEffect(() => {
    return subscribe((event, payload) => {
      if (event === 'gas_monitor_updated') {
        setMonitors((prev) =>
          prev.some((m) => m.id === payload.id)
            ? prev.map((m) => (m.id === payload.id ? payload : m))
            : [...prev, payload].sort((a, b) => a.monitor_id.localeCompare(b.monitor_id)),
        )
      } else if (event === 'gas_monitor_deleted') {
        setMonitors((prev) => prev.filter((m) => m.id !== payload.id))
      } else if (event === 'resync') {
        void fetchMonitors()
      }
    })
  }, [subscribe, fetchMonitors])

  useEffect(() => {
    if (!poll) return undefined
    const timer = window.setInterval(fetchMonitors, POLL_MS)
    return () => window.clearInterval(timer)
  }, [fetchMonitors, poll])

  return { monitors, loading, error, fetchMonitors, createMonitor, updateMonitor, deleteMonitor }
}
