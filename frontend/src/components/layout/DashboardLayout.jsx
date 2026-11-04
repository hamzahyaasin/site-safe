import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { cn } from '../../lib/utils.js'
import { useDashboardStats } from '../../hooks/useDashboardStats.js'
import Sidebar from './Sidebar.jsx'
import Topbar from './Topbar.jsx'
import ConnectionToast from './ConnectionToast.jsx'
import { pageTitle } from './navConfig.js'

const COLLAPSED_KEY = 'sitesafe_sidebar_collapsed'

function readCollapsed() {
  try {
    return localStorage.getItem(COLLAPSED_KEY) === '1'
  } catch {
    return false
  }
}

export default function DashboardLayout() {
  const [collapsed, setCollapsed] = useState(readCollapsed)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { stats } = useDashboardStats()
  const { pathname } = useLocation()

  useEffect(() => {
    document.title = `${pageTitle(pathname)} · Site-Safe`
    window.scrollTo(0, 0)
  }, [pathname])

  function toggleCollapsed() {
    setCollapsed((c) => {
      try {
        localStorage.setItem(COLLAPSED_KEY, c ? '0' : '1')
      } catch {
        // Not remembered in a private window; the toggle still works.
      }
      return !c
    })
  }

  return (
    <div className="min-h-screen bg-[#0F1117]">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-[80] focus:rounded-md focus:bg-amber-500 focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-zinc-950"
      >
        Skip to content
      </a>
      <Sidebar
        collapsed={collapsed}
        onToggle={toggleCollapsed}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        unresolvedCount={stats?.unresolved_alerts || 0}
      />
      <div
        className={cn(
          'flex min-h-screen min-w-0 flex-col transition-[margin] duration-200',
          collapsed ? 'lg:ml-16' : 'lg:ml-60',
        )}
      >
        <Topbar onOpenMobileNav={() => setMobileOpen(true)} />
        <main id="main" className="flex-1 px-4 py-6 sm:px-6 lg:py-8">
          <div className="mx-auto max-w-[1600px]">
            <Outlet />
          </div>
        </main>
      </div>
      <ConnectionToast />
    </div>
  )
}
