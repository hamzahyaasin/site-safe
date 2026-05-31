import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'

function normalizeList(data) {
  return Array.isArray(data) ? data : data?.results || []
}

export function useZones() {
  const { api } = useAuth()
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
    loadZones()
  }, [loadZones])

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
