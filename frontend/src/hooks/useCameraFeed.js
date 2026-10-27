import { useEffect, useRef, useState } from 'react'
import { refreshAccessToken, storageKeys } from '../api/axios.js'

const DASHBOARD_WS = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000/ws/dashboard/'
const CAMERAS_WS = DASHBOARD_WS.replace(/\/ws\/dashboard\/.*$/, '/ws/cameras/')
// Server close codes (alerts/consumers.py).
const CLOSE_UNAUTHORIZED = 4401
const CLOSE_FORBIDDEN = 4403
const RETRY_MS = 3000
const NEWLINE = 10

/**
 * Live frames for the Cameras page over /ws/cameras/.
 *
 * Each binary message is "<camera_id>\n<jpeg>". Returns
 * { frames: {camera_id: {url, at}}, status } where url is an object URL of
 * the newest JPEG (the previous one is revoked) and at is when it arrived.
 * The socket is open only while the page is mounted.
 */
export function useCameraFeed(enabled) {
  const [frames, setFrames] = useState({})
  const [status, setStatus] = useState('connecting')
  const urlsRef = useRef({})

  useEffect(() => {
    if (!enabled) return undefined
    let ws = null
    let retryTimer = null
    let stopped = false

    const connect = () => {
      const token = localStorage.getItem(storageKeys.access) || ''
      ws = new WebSocket(`${CAMERAS_WS}?token=${encodeURIComponent(token)}`)
      ws.binaryType = 'arraybuffer'
      ws.onopen = () => setStatus('live')
      ws.onmessage = (evt) => {
        if (!(evt.data instanceof ArrayBuffer)) return
        const bytes = new Uint8Array(evt.data)
        const split = bytes.indexOf(NEWLINE)
        if (split <= 0) return
        const cameraId = new TextDecoder().decode(bytes.subarray(0, split))
        const url = URL.createObjectURL(new Blob([bytes.subarray(split + 1)], { type: 'image/jpeg' }))
        const previous = urlsRef.current[cameraId]
        urlsRef.current[cameraId] = url
        setFrames((prev) => ({ ...prev, [cameraId]: { url, at: Date.now() } }))
        if (previous) URL.revokeObjectURL(previous)
      }
      ws.onclose = (evt) => {
        if (stopped) return
        if (evt.code === CLOSE_FORBIDDEN) {
          setStatus('forbidden')
          return
        }
        setStatus('reconnecting')
        const retry = () => {
          retryTimer = window.setTimeout(connect, RETRY_MS)
        }
        if (evt.code === CLOSE_UNAUTHORIZED) {
          refreshAccessToken().then(connect, retry)
        } else {
          retry()
        }
      }
    }

    connect()
    const urls = urlsRef.current
    return () => {
      stopped = true
      window.clearTimeout(retryTimer)
      if (ws) ws.close()
      Object.values(urls).forEach((u) => URL.revokeObjectURL(u))
      urlsRef.current = {}
    }
  }, [enabled])

  return { frames, status }
}
