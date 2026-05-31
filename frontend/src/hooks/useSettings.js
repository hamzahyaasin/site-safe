import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'

function normalizeList(data) {
  return Array.isArray(data) ? data : data?.results || []
}

export function useSettings() {
  const { api } = useAuth()

  const [alertConfigs, setAlertConfigs] = useState([])
  const [profile, setProfile] = useState(null)
  const [loadingConfigs, setLoadingConfigs] = useState(true)
  const [loadingProfile, setLoadingProfile] = useState(true)
  const [error, setError] = useState(null)

  const loadAlertConfigs = useCallback(async () => {
    setLoadingConfigs(true)
    try {
      const { data } = await api.get('v1/alert-config/')
      setAlertConfigs(normalizeList(data))
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load alert configuration')
      setAlertConfigs([])
    } finally {
      setLoadingConfigs(false)
    }
  }, [api])

  const loadProfile = useCallback(async () => {
    setLoadingProfile(true)
    try {
      const { data } = await api.get('v1/profile/')
      setProfile(data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load profile')
    } finally {
      setLoadingProfile(false)
    }
  }, [api])

  const updateAlertConfig = useCallback(
    async (id, payload) => {
      const { data } = await api.patch(`v1/alert-config/${id}/`, payload)
      setAlertConfigs((prev) => prev.map((row) => (row.id === id ? { ...row, ...data } : row)))
      return data
    },
    [api],
  )

  const updateNotifications = useCallback(
    async (payload) => {
      const { data } = await api.patch('v1/profile/', payload)
      setProfile(data)
      return data
    },
    [api],
  )

  const changePassword = useCallback(
    async ({ current_password, new_password }) => {
      await api.post('v1/profile/change-password/', { current_password, new_password })
    },
    [api],
  )

  useEffect(() => {
    loadAlertConfigs()
    loadProfile()
  }, [loadAlertConfigs, loadProfile])

  return {
    alertConfigs,
    profile,
    loadingConfigs,
    loadingProfile,
    error,
    loadAlertConfigs,
    loadProfile,
    updateAlertConfig,
    updateNotifications,
    changePassword,
  }
}
