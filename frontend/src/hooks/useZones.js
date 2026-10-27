import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { useWebSocketContext } from './useWebSocketContext.js'

function normalizeList(data) {
  return Array.isArray(data) ? data : data?.results || []
}

export function useZones() {
  const { api } = useAuth()
  const { subscribe } = useWebSocketContext()
  const [zones, setZones] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadZones = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get('v1/zones/')
      setZones(normalizeList(data))
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load zones')
      setZones([])
    } finally {
      setLoading(false)
    }
  }, [api])

  const createZone = useCallback(
    async (payload) => {
      const { data } = await api.post('v1/zones/', payload)
      await loadZones()
      return data
    },
    [api, loadZones],
  )

  const updateZone = useCallback(
    async (id, payload) => {
      const { data } = await api.put(`v1/zones/${id}/`, payload)
      await loadZones()
      return data
    },
    [api, loadZones],
  )

  const deleteZone = useCallback(
    async (id) => {
      await api.delete(`v1/zones/${id}/`)
      await loadZones()
    },
    [api, loadZones],
  )

  useEffect(() => {
    // Deferred so the initial load's state updates happen outside the effect body.
    const t = window.setTimeout(() => {
      loadZones()
    }, 0)
    return () => window.clearTimeout(t)
  }, [loadZones])

  // Head counts change as cameras report and workers move: take each live update.
  useEffect(
    () =>
      subscribe((event, payload) => {
        if (event === 'zone_updated' && payload?.id) {
          setZones((prev) => prev.map((z) => (z.id === payload.id ? payload : z)))
        }
      }),
    [subscribe],
  )

  return {
    zones,
    loading,
    error,
    loadZones,
    createZone,
    updateZone,
    deleteZone,
  }
}
