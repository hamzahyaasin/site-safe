import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { normalizeList } from '../lib/utils.js'

/** Current (active or upcoming, not revoked) hot-work permits. */
export function useHotWorkPermits() {
  const { api } = useAuth()
  const [permits, setPermits] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('v1/hot-work-permits/', { params: { state: 'current' } })
      setPermits(normalizeList(data))
      setError('')
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load permits')
    } finally {
      setLoading(false)
    }
  }, [api])

  useEffect(() => {
    const first = window.setTimeout(load, 0)
    // Permits start and expire on their own; refresh so status stays true.
    const timer = window.setInterval(load, 60000)
    return () => {
      window.clearTimeout(first)
      window.clearInterval(timer)
    }
  }, [load])

  const issue = useCallback(
    async (body) => {
      await api.post('v1/hot-work-permits/', body)
      await load()
    },
    [api, load],
  )

  const revoke = useCallback(
    async (id) => {
      await api.post(`v1/hot-work-permits/${id}/revoke/`)
      await load()
    },
    [api, load],
  )

  return { permits, loading, error, issue, revoke, reload: load }
}
