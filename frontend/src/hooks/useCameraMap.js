import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { useWebSocketContext } from './useWebSocketContext.js'

// Live status follows the camera's frames, which have no event of their own.
const POLL_MS = 10000
// How long a camera stays highlighted on the map after it raises an alert.
export const ALERT_FLASH_MS = 60000

/** 'alerting' for a minute after a new alert, else 'live' or 'offline'. */
export function cameraStatus(camera, alerting) {
  if (alerting?.[camera.camera_id]) return 'alerting'
  return camera.live ? 'live' : 'offline'
}

/**
 * Cameras for the site map (FR-33): placement, live status, people in view
 * and alerts, from /api/v1/camera-map/. Rows update live on
 * ``camera_updated``; an ``alert_created`` from a camera marks it as
 * alerting for ALERT_FLASH_MS.
 */
export function useCameraMap() {
  const { api } = useAuth()
  const { subscribe } = useWebSocketContext()
  const [cameras, setCameras] = useState([])
  const [alerting, setAlerting] = useState({}) // camera_id -> time of its last new alert
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('v1/camera-map/')
      setCameras(Array.isArray(data) ? data : [])
      setError(null)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Could not load the cameras.')
    }
  }, [api])

  useEffect(() => {
    const first = window.setTimeout(load, 0)
    const timer = window.setInterval(load, POLL_MS)
    return () => {
      window.clearTimeout(first)
      window.clearInterval(timer)
    }
  }, [load])

  useEffect(
    () =>
      subscribe((event, payload) => {
        if (event === 'camera_updated' && payload?.camera_id) {
          setCameras((prev) =>
            prev.some((c) => c.camera_id === payload.camera_id)
              ? prev.map((c) => (c.camera_id === payload.camera_id ? payload : c))
              : [...prev, payload].sort((a, b) => a.camera_id.localeCompare(b.camera_id)),
          )
        } else if (event === 'alert_created' && payload?.camera_id) {
          setAlerting((prev) => ({ ...prev, [payload.camera_id]: Date.now() }))
          void load()
        } else if (event === 'alert_resolved' && payload?.camera_id) {
          void load()
        } else if (event === 'resync') {
          void load()
        }
      }),
    [subscribe, load],
  )

  // Drop highlights once they have run their time.
  useEffect(() => {
    const ids = Object.keys(alerting)
    if (ids.length === 0) return undefined
    const next = Math.min(...ids.map((id) => alerting[id])) + ALERT_FLASH_MS - Date.now()
    const t = window.setTimeout(
      () => setAlerting((prev) => Object.fromEntries(Object.entries(prev).filter(([, at]) => Date.now() - at < ALERT_FLASH_MS))),
      Math.max(0, next),
    )
    return () => window.clearTimeout(t)
  }, [alerting])

  const place = useCallback(
    async (cameraId, placement) => {
      const { data } = await api.put(`v1/camera-map/${encodeURIComponent(cameraId)}/`, placement)
      setCameras((prev) => prev.map((c) => (c.camera_id === cameraId ? data : c)))
      return data
    },
    [api],
  )

  const unplace = useCallback(
    async (cameraId) => {
      await api.delete(`v1/camera-map/${encodeURIComponent(cameraId)}/`)
      setCameras((prev) => prev.map((c) => (c.camera_id === cameraId ? { ...c, placement: null } : c)))
    },
    [api],
  )

  return { cameras, alerting, error, reload: load, place, unplace }
}
