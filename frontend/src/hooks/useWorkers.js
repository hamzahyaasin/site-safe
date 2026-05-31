import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'

function normalizeList(data) {
  return Array.isArray(data) ? data : data?.results || []
}

export function useWorkers() {
  const { api } = useAuth()
  const [workers, setWorkers] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchWorkers = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get('workers/')
      setWorkers(normalizeList(data))
    } finally {
      setLoading(false)
    }
  }, [api])

  useEffect(() => {
    fetchWorkers()
  }, [fetchWorkers])

  return { workers, loading, fetchWorkers }
}
