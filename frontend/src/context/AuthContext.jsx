import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import api, { API_BASE_URL, TOKEN_EVENT, clearTokens, storageKeys, storeTokens } from '../api/axios.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem(storageKeys.access))
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem(storageKeys.email))
  const [role, setRole] = useState(null)

  const isAuthenticated = Boolean(accessToken)

  // Follow token changes made outside React (automatic refresh, forced logout).
  useEffect(() => {
    const onToken = (e) => setAccessToken(e.detail)
    window.addEventListener(TOKEN_EVENT, onToken)
    return () => window.removeEventListener(TOKEN_EVENT, onToken)
  }, [])

  // The role is authoritative on the server; this copy only drives which
  // controls are offered. The API refuses a disallowed write regardless of
  // what the interface shows.
  useEffect(() => {
    if (!accessToken) {
      setRole(null)
      return
    }
    let cancelled = false
    api
      .get('v1/profile/')
      .then(({ data }) => {
        if (!cancelled) setRole(data.role ?? null)
      })
      .catch(() => {
        if (!cancelled) setRole(null)
      })
    return () => {
      cancelled = true
    }
  }, [accessToken])

  const login = useCallback(async (email, password) => {
    const { data } = await axios.post(`${API_BASE_URL}token/`, { email, password })
    localStorage.setItem(storageKeys.email, email)
    storeTokens(data)
    setAccessToken(data.access)
    setUserEmail(email)
  }, [])

  const logout = useCallback(() => {
    clearTokens()
    setAccessToken(null)
    setUserEmail(null)
  }, [])

  const value = useMemo(
    () => ({
      isAuthenticated,
      userEmail,
      role,
      isAdmin: role === 'ADMIN',
      // Admin outranks Safety Officer, so it satisfies this too.
      canOperate: role === 'ADMIN' || role === 'SAFETY_OFFICER',
      isViewer: role === 'VIEWER',
      login,
      logout,
      api,
    }),
    [isAuthenticated, userEmail, role, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return ctx
}
