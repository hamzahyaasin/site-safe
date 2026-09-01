import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { cn } from '../../lib/utils.js'
import { useDashboardStats } from '../../hooks/useDashboardStats.js'
import Sidebar from './Sidebar.jsx'
import Topbar from './Topbar.jsx'
import ConnectionToast from './ConnectionToast.jsx'

export default function DashboardLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [siteId, setSiteId] = useState('site-a')
  const { stats } = useDashboardStats()

  return (
    <div className="min-h-screen bg-[#0F1117]">
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((c) => !c)}
        unresolvedCount={stats?.unresolved_alerts || 0}
      />
      <div
        className={cn(
          'flex min-h-screen flex-col transition-[margin] duration-200',
          collapsed ? 'ml-16' : 'ml-60',
        )}
      >
        <Topbar siteId={siteId} onSiteChange={setSiteId} />
        <main className="flex-1 p-6">
          <div className="mx-auto max-w-[1600px]">
            <Outlet context={{ siteId }} />
          </div>
        </main>
      </div>
      <ConnectionToast />
    </div>
  )
}
