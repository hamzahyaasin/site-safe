import { createContext, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './AuthContext.jsx'
import { refreshAccessToken, storageKeys } from '../api/axios.js'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000/ws/dashboard/'
const POLL_MS = 5000
const MAX_WS_RETRIES = 5
const RECONNECT_DELAY_MS = 8000
// Server close code for a missing/expired access token (alerts/consumers.py).
const CLOSE_UNAUTHORIZED = 4401
// Server events re-emitted to subscribers unchanged.
const FORWARDED_EVENTS = new Set([
  'alert_updated',
  'alert_resolved',
  'vest_updated',
  'worker_status_update',
  'zone_updated',
  'camera_updated',
  'gas_monitor_updated',
  'gas_monitor_deleted',
])

function socketUrl() {
  const token = localStorage.getItem(storageKeys.access) || ''
  const sep = WS_URL.includes('?') ? '&' : '?'
  return `${WS_URL}${sep}token=${encodeURIComponent(token)}`
}

// eslint-disable-next-line react-refresh/only-export-components -- context consumed by useWebSocketContext hook
export const WebSocketContext = createContext(null)

export function WebSocketProvider({ children }) {
  const { api, isAuthenticated } = useAuth()
  const [status, setStatus] = useState('reconnecting')
  const [unreadAlerts, setUnreadAlerts] = useState(0)
  const [bellPulse, setBellPulse] = useState(false)
  const [connectionToast, setConnectionToast] = useState(null)
  const listenersRef = useRef(new Set())
  const wsRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const knownAlertIdsRef = useRef(new Set())
  const pollTimerRef = useRef(null)
  const connectWebSocketRef = useRef(() => {})
  const wsRetryCountRef = useRef(0)
  const prevStatusRef = useRef('reconnecting')
  const hasConnectedRef = useRef(false)

  const emit = useCallback((event, payload) => {
    listenersRef.current.forEach((fn) => {
      try {
        fn(event, payload)
      } catch {
        /* subscriber error */
      }
    })
  }, [])

  const subscribe = useCallback((fn) => {
    listenersRef.current.add(fn)
    return () => listenersRef.current.delete(fn)
  }, [])

  const pulseBell = useCallback(() => {
    setBellPulse(true)
    window.setTimeout(() => setBellPulse(false), 600)
  }, [])

  const updateStatus = useCallback((next) => {
    const prev = prevStatusRef.current
    if (prev === 'live' && next === 'reconnecting') {
      setConnectionToast({
        message: 'Live connection lost. Retrying…',
        type: 'warning',
      })
    }
    if (next === 'live') {
      setConnectionToast(null)
    }
    if (next === 'offline' && prev !== 'offline') {
      setConnectionToast({
        message: 'Unable to establish live connection. Data may be delayed.',
        type: 'error',
      })
    }
    prevStatusRef.current = next
    setStatus(next)
  }, [])

  const handleNewAlerts = useCallback(
    (alerts) => {
      const fresh = []
      for (const alert of alerts) {
        if (!knownAlertIdsRef.current.has(alert.id)) {
          fresh.push(alert)
          knownAlertIdsRef.current.add(alert.id)
        }
      }
      if (knownAlertIdsRef.current.size === 0 && alerts.length > 0) {
        alerts.forEach((a) => knownAlertIdsRef.current.add(a.id))
        return
      }
      if (fresh.length > 0) {
        fresh.forEach((alert) => emit('alert_created', alert))
        setUnreadAlerts((n) => n + fresh.length)
        pulseBell()
      }
    },
    [emit, pulseBell],
  )

  const pollAlerts = useCallback(async () => {
    if (!api) return
    try {
      const { data } = await api.get('alerts/', {
        params: { is_resolved: 'false', ordering: '-timestamp' },
      })
      const list = Array.isArray(data) ? data : data.results || []
      handleNewAlerts(list)
    } catch {
      /* polling error */
    }
  }, [api, handleNewAlerts])

  const pollWorkers = useCallback(async () => {
    if (!api) return
    try {
      const { data } = await api.get('workers/')
      const list = Array.isArray(data) ? data : data.results || []
      emit('workers_refreshed', list)
    } catch {
      /* polling error */
    }
  }, [api, emit])

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      window.clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }, [])

  const startPolling = useCallback(() => {
    if (pollTimerRef.current) return
    pollAlerts()
    pollWorkers()
    pollTimerRef.current = window.setInterval(() => {
      pollAlerts()
      pollWorkers()
    }, POLL_MS)
  }, [pollAlerts, pollWorkers])

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      window.clearTimeout(reconnectTimerRef.current)
    }
    if (wsRetryCountRef.current >= MAX_WS_RETRIES) {
      updateStatus('offline')
      return
    }
    updateStatus('reconnecting')
    reconnectTimerRef.current = window.setTimeout(() => {
      connectWebSocketRef.current()
    }, RECONNECT_DELAY_MS)
  }, [updateStatus])

  const connectWebSocket = useCallback(() => {
    if (!isAuthenticated) return
    if (wsRetryCountRef.current >= MAX_WS_RETRIES) {
      updateStatus('offline')
      startPolling()
      return
    }

    try {
      const ws = new WebSocket(socketUrl())
      wsRef.current = ws
      updateStatus('reconnecting')

      ws.onopen = () => {
        wsRetryCountRef.current = 0
        updateStatus('live')
        stopPolling()
        // Events published while the socket was down were missed, so ask
        // every subscriber to reload its state from the API.
        if (hasConnectedRef.current) emit('resync', null)
        hasConnectedRef.current = true
      }

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data)
          if (msg.type === 'alert_created') {
            emit('alert_created', msg.payload)
            setUnreadAlerts((n) => n + 1)
            pulseBell()
          } else if (FORWARDED_EVENTS.has(msg.type)) {
            emit(msg.type, msg.payload)
          }
        } catch {
          /* invalid message */
        }
      }

      ws.onclose = (evt) => {
        if (wsRef.current !== ws) return
        wsRef.current = null
        startPolling()
        if (evt.code === CLOSE_UNAUTHORIZED) {
          // Expired access token: renew it and reconnect straight away. A
          // failed refresh is handled by the axios layer (sign-out).
          refreshAccessToken()
            .then(() => connectWebSocketRef.current())
            .catch(() => {
              wsRetryCountRef.current += 1
              scheduleReconnect()
            })
          return
        }
        wsRetryCountRef.current += 1
        scheduleReconnect()
      }

      ws.onerror = () => {
        ws.close()
      }
    } catch {
      wsRetryCountRef.current += 1
      startPolling()
      scheduleReconnect()
    }
  }, [isAuthenticated, emit, pulseBell, startPolling, stopPolling, scheduleReconnect, updateStatus])

  useEffect(() => {
    connectWebSocketRef.current = connectWebSocket
  }, [connectWebSocket])

  useEffect(() => {
    if (!isAuthenticated) {
      knownAlertIdsRef.current = new Set()
      wsRetryCountRef.current = 0
      hasConnectedRef.current = false
      prevStatusRef.current = 'reconnecting'
      // eslint-disable-next-line react-hooks/set-state-in-effect -- reset toast on logout
      setConnectionToast(null)
      stopPolling()
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current)
      }
      return undefined
    }

    wsRetryCountRef.current = 0
    connectWebSocket()
    return () => {
      stopPolling()
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current)
      }
    }
  }, [isAuthenticated, connectWebSocket, stopPolling])

  const clearUnread = useCallback(() => setUnreadAlerts(0), [])

  const dismissConnectionToast = useCallback(() => setConnectionToast(null), [])

  const connectionStatus = isAuthenticated ? status : 'offline'

  const value = useMemo(
    () => ({
      status: connectionStatus,
      subscribe,
      unreadAlerts,
      bellPulse,
      clearUnread,
      connectionToast,
      dismissConnectionToast,
    }),
    [connectionStatus, subscribe, unreadAlerts, bellPulse, clearUnread, connectionToast, dismissConnectionToast],
  )

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>
}
