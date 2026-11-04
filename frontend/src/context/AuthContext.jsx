import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import api, { API_BASE_URL, TOKEN_EVENT, clearTokens, storageKeys, storeTokens } from '../api/axios.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem(storageKeys.access))
  const [storedEmail, setStoredEmail] = useState(() => localStorage.getItem(storageKeys.email))
  // The signed-in identity comes from the server, not from what was typed at
  // login: a differently-cased email, or a token left over from another
  // account, must not leave the user without their role. Cleared on every
  // login and logout so a role never carries over to a different account.
  const [profile, setProfile] = useState(null)
  const role = accessToken ? (profile?.role ?? null) : null
  const userEmail = profile?.email ?? storedEmail

  const isAuthenticated = Boolean(accessToken)

  // Follow token changes made outside React (automatic refresh, forced logout).
  useEffect(() => {
    const onToken = (e) => {
      setAccessToken(e.detail)
      if (!e.detail) setProfile(null)
    }
    window.addEventListener(TOKEN_EVENT, onToken)
    return () => window.removeEventListener(TOKEN_EVENT, onToken)
  }, [])

  // The role is authoritative on the server; this copy only drives which
  // controls are offered. The API refuses a disallowed write regardless of
  // what the interface shows.
  useEffect(() => {
    if (!accessToken) return undefined
    let cancelled = false
    api
      .get('v1/profile/')
      .then(({ data }) => {
        if (cancelled) return
        setProfile({ email: data.email, role: data.role ?? null, fullName: data.full_name || '' })
        if (data.email) localStorage.setItem(storageKeys.email, data.email)
      })
      .catch(() => {
        if (!cancelled) setProfile(null)
      })
    return () => {
      cancelled = true
    }
  }, [accessToken])

  const login = useCallback(async (email, password) => {
    const { data } = await axios.post(`${API_BASE_URL}token/`, { email, password })
    setProfile(null)
    localStorage.setItem(storageKeys.email, email)
    setStoredEmail(email)
    storeTokens(data)
    setAccessToken(data.access)
  }, [])

  const logout = useCallback(() => {
    clearTokens()
    setProfile(null)
    setAccessToken(null)
    setStoredEmail(null)
  }, [])

  const value = useMemo(
    () => ({
      isAuthenticated,
      userEmail,
      fullName: profile?.fullName || '',
      role,
      isAdmin: role === 'ADMIN',
      // Admin outranks Safety Officer, so it satisfies this too.
      canOperate: role === 'ADMIN' || role === 'SAFETY_OFFICER',
      isViewer: role === 'VIEWER',
      login,
      logout,
      api,
    }),
    [isAuthenticated, userEmail, profile, role, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components -- hook co-located with its provider
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return ctx
}
