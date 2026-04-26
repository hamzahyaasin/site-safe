import axios from 'axios'

const ACCESS_KEY = 'sitesafe_access'
const REFRESH_KEY = 'sitesafe_refresh'
const EMAIL_KEY = 'sitesafe_email'

export const storageKeys = {
  access: ACCESS_KEY,
  refresh: REFRESH_KEY,
  email: EMAIL_KEY,
}

const api = axios.create({
  baseURL: 'http://localhost:8000/api/',
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

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    if (status === 401) {
      localStorage.removeItem(ACCESS_KEY)
      localStorage.removeItem(REFRESH_KEY)
      localStorage.removeItem(EMAIL_KEY)
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default api
