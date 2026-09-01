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
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async data load on mount
    void fetchWorkers()
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
      }
    })
  }, [subscribe])

  const createWorker = useCallback(
    async (body) => {
      await api.post('workers/', { ...body, is_active: true })
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
