import { Link } from 'react-router-dom'
import { initials } from '../../lib/utils.js'
import { useAuth } from '../../context/AuthContext.jsx'
import { useWebSocket } from '../../hooks/useWebSocket.js'

const ROLE_LABEL = { ADMIN: 'Admin', SAFETY_OFFICER: 'Safety Officer', VIEWER: 'Viewer' }

// Single-site deployment: the API has no site model, so no site switcher
// is offered. Set VITE_SITE_NAME to label the site.
const SITE_NAME = import.meta.env.VITE_SITE_NAME || 'Site-Safe'

export default function Topbar() {
  const { userEmail, role } = useAuth()
  const { unreadAlerts, bellPulse, clearUnread } = useWebSocket()

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-4 border-b border-zinc-800 bg-[#0f1117]/95 px-6 backdrop-blur-sm">
      <div className="flex min-w-0 items-center gap-4">
        <p className="truncate text-sm font-medium text-zinc-300">{SITE_NAME}</p>
      </div>

      <div className="flex items-center gap-3">
        <Link
          to="/incidents"
          onClick={clearUnread}
          className={`relative flex h-9 w-9 items-center justify-center rounded-md border border-zinc-800 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500${
            bellPulse ? ' animate-bell-pulse' : ''
          }`}
          aria-label={`Alerts${unreadAlerts ? `, ${unreadAlerts} unread` : ''}`}
        >
          <IconBell className="h-4 w-4" />
          {unreadAlerts > 0 ? (
            <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
              {unreadAlerts > 9 ? '9+' : unreadAlerts}
            </span>
          ) : null}
        </Link>

        <div className="flex items-center gap-2 rounded-md border border-zinc-800 bg-zinc-900/50 py-1 pl-1 pr-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-amber-500/15 text-xs font-semibold text-amber-400">
            {initials(userEmail?.split('@')[0] || 'U')}
          </div>
          <div className="hidden text-left sm:block">
            <p className="max-w-[140px] truncate text-xs font-medium text-zinc-200">
              {userEmail?.split('@')[0] || 'User'}
            </p>
            <p className="text-[10px] text-zinc-500">{ROLE_LABEL[role] ?? '…'}</p>
          </div>
        </div>
      </div>
    </header>
  )
}

function IconBell({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  )
}
