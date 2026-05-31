import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'

function normalizeList(data) {
  return Array.isArray(data) ? data : data?.results || []
}

const POLL_MS = 10000

export function useVests(options = {}) {
  const { poll = true } = options
  const { api } = useAuth()
  const [vests, setVests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchVests = useCallback(async () => {
    try {
      const { data } = await api.get('v1/vests/')
      setVests(normalizeList(data))
      setError(null)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load vests')
      setVests([])
    } finally {
      setLoading(false)
    }
  }, [api])

  const createVest = useCallback(
    async (payload) => {
      const { data } = await api.post('v1/vests/', payload)
      await fetchVests()
      return data
    },
    [api, fetchVests],
  )

  const updateVest = useCallback(
    async (id, payload) => {
      const { data } = await api.patch(`v1/vests/${id}/`, payload)
      setVests((prev) => prev.map((v) => (v.id === id ? { ...v, ...data } : v)))
      return data
    },
    [api],
  )

  const deleteVest = useCallback(
    async (id) => {
      await api.delete(`v1/vests/${id}/`)
      await fetchVests()
    },
    [api, fetchVests],
  )

  useEffect(() => {
    fetchVests()
  }, [fetchVests])

  useEffect(() => {
    if (!poll) return undefined
    const timer = window.setInterval(fetchVests, POLL_MS)
    return () => window.clearInterval(timer)
  }, [fetchVests, poll])

  return {
    vests,
    loading,
    error,
    fetchVests,
    createVest,
    updateVest,
    deleteVest,
  }
}
