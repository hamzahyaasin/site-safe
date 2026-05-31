import { useEffect, useRef } from 'react'

function wsUrl() {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = import.meta.env.VITE_WS_HOST || `${window.location.hostname}:8000`
  return `${protocol}//${host}/ws/dashboard/default/`
}

export function useWebSocket(onAlert) {
  const onAlertRef = useRef(onAlert)
  onAlertRef.current = onAlert

  useEffect(() => {
    let ws
    let reconnectTimer
    let closed = false

    function connect() {
      ws = new WebSocket(wsUrl())

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'alert_created') {
          onAlertRef.current(data.payload)
        }
      }

      ws.onclose = () => {
        if (!closed) {
          reconnectTimer = window.setTimeout(connect, 3000)
        }
      }
    }

    connect()

    return () => {
      closed = true
      window.clearTimeout(reconnectTimer)
      ws?.close()
    }
  }, [])
}
