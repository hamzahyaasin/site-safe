import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import axios from 'axios'
import api, { storageKeys } from '../api/axios.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem(storageKeys.access))
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem(storageKeys.email))

  const isAuthenticated = Boolean(accessToken)

  const login = useCallback(async (email, password) => {
    const tokenUrl = 'http://localhost:8000/api/token/'
    const { data } = await axios.post(tokenUrl, { email, password })
    localStorage.setItem(storageKeys.access, data.access)
    localStorage.setItem(storageKeys.refresh, data.refresh)
    localStorage.setItem(storageKeys.email, email)
    setAccessToken(data.access)
    setUserEmail(email)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(storageKeys.access)
    localStorage.removeItem(storageKeys.refresh)
    localStorage.removeItem(storageKeys.email)
    setAccessToken(null)
    setUserEmail(null)
  }, [])

  const value = useMemo(
    () => ({
      isAuthenticated,
      userEmail,
      login,
      logout,
      api,
    }),
    [isAuthenticated, userEmail, login, logout],
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
