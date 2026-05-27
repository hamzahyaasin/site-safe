import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import Sidebar from './Sidebar.jsx'

export default function AppLayout() {
  const { api } = useAuth()
  const [alertCount, setAlertCount] = useState(0)

  useEffect(() => {
    async function fetchCount() {
      try {
        const { data } = await api.get('dashboard/stats/')
        setAlertCount(data.unresolved_alerts || 0)
      } catch {
        // silently skip if stats endpoint is unavailable
      }
    }
    fetchCount()
    const t = setInterval(fetchCount, 15000)
    return () => clearInterval(t)
  }, [api])

  return (
    <div className="app-shell">
      <Sidebar alertCount={alertCount} />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
