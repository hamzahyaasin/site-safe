import axios from 'axios'

const ACCESS_KEY = 'sitesafe_access'
const REFRESH_KEY = 'sitesafe_refresh'
const EMAIL_KEY = 'sitesafe_email'

export const storageKeys = {
  access: ACCESS_KEY,
  refresh: REFRESH_KEY,
  email: EMAIL_KEY,
}

export const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/').replace(
  /\/?$/,
  '/',
)

// Fired on window whenever the access token changes (login, refresh, logout)
// so the auth context and websocket can follow without a page reload.
export const TOKEN_EVENT = 'sitesafe:token'

function announceToken(token) {
  window.dispatchEvent(new CustomEvent(TOKEN_EVENT, { detail: token }))
}

export function storeTokens({ access, refresh }) {
  localStorage.setItem(ACCESS_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  announceToken(access)
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem(EMAIL_KEY)
  announceToken(null)
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(ACCESS_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// One refresh at a time: concurrent 401s wait on the same request.
let refreshInFlight = null

export function refreshAccessToken() {
  if (refreshInFlight) return refreshInFlight
  const refresh = localStorage.getItem(REFRESH_KEY)
  if (!refresh) return Promise.reject(new Error('No refresh token'))
  refreshInFlight = axios
    .post(`${API_BASE_URL}token/refresh/`, { refresh })
    .then(({ data }) => {
      storeTokens(data)
      return data.access
    })
    .finally(() => {
      refreshInFlight = null
    })
  return refreshInFlight
}

function sendToLogin() {
  clearTokens()
  if (!window.location.pathname.startsWith('/login')) {
    window.location.href = '/login'
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && original && !original._retried) {
      original._retried = true
      try {
        const access = await refreshAccessToken()
        original.headers.Authorization = `Bearer ${access}`
        return api(original)
      } catch {
        sendToLogin()
      }
    } else if (error.response?.status === 401) {
      sendToLogin()
    }
    return Promise.reject(error)
  },
)

export default api
