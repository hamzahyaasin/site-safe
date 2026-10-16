import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { useWebSocketContext } from './useWebSocketContext.js'
import { normalizeList } from '../lib/utils.js'

export function useWorkers() {
  const { api } = useAuth()
  const { subscribe } = useWebSocketContext()
  const [workers, setWorkers] = useState([])
  const [loading, setLoading] = useState(true)
  const [highlightIds, setHighlightIds] = useState(() => new Set())

  const fetchWorkers = useCallback(async () => {
    const { data } = await api.get('workers/')
    setWorkers(normalizeList(data))
    setLoading(false)
  }, [api])

  useEffect(() => {
    const first = window.setTimeout(fetchWorkers, 0)
    // Presence depends on how recently each vest reported, so refresh even
    // when no event arrives.
    const timer = window.setInterval(fetchWorkers, 60000)
    return () => {
      window.clearTimeout(first)
      window.clearInterval(timer)
    }
  }, [fetchWorkers])

  useEffect(() => {
    return subscribe((event, payload) => {
      if (event === 'worker_status_update') {
        setWorkers((prev) =>
          prev.map((w) => (w.id === payload.id ? { ...w, ...payload } : w)),
        )
        setHighlightIds((prev) => new Set(prev).add(payload.id))
        window.setTimeout(() => {
          setHighlightIds((prev) => {
            const next = new Set(prev)
            next.delete(payload.id)
            return next
          })
        }, 1200)
      } else if (event === 'workers_refreshed') {
        setWorkers(payload)
      } else if (event === 'resync') {
        void fetchWorkers()
      }
    })
  }, [subscribe, fetchWorkers])

  const createWorker = useCallback(
    async (body) => {
      await api.post('workers/', { is_active: true, ...body })
      await fetchWorkers()
    },
    [api, fetchWorkers],
  )

  const updateWorker = useCallback(
    async (id, body) => {
      await api.patch(`workers/${id}/`, body)
      await fetchWorkers()
    },
    [api, fetchWorkers],
  )

  const deleteWorker = useCallback(
    async (id) => {
      await api.delete(`workers/${id}/`)
      await fetchWorkers()
    },
    [api, fetchWorkers],
  )

  return {
    workers,
    loading,
    highlightIds,
    fetchWorkers,
    createWorker,
    updateWorker,
    deleteWorker,
  }
}
