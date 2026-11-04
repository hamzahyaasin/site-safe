import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { cn, initials } from '../../lib/utils.js'
import { useAuth } from '../../context/AuthContext.jsx'
import { useWebSocket } from '../../hooks/useWebSocket.js'
import { IconBell, IconChevronDown, IconLogout, IconMenu, IconSettings, IconUser } from '../ui/icons.jsx'
import { pageTitle } from './navConfig.js'

const ROLE_LABEL = { ADMIN: 'Admin', SAFETY_OFFICER: 'Safety Officer', VIEWER: 'Viewer' }

// Single-site deployment: the API has no site model, so no site switcher
// is offered. Set VITE_SITE_NAME to label the site.
const SITE_NAME = import.meta.env.VITE_SITE_NAME || 'Site-Safe'

export default function Topbar({ onOpenMobileNav }) {
  const { pathname } = useLocation()
  const { unreadAlerts, bellPulse, clearUnread } = useWebSocket()

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-3 border-b border-zinc-800/80 bg-[#0f1117]/90 px-4 backdrop-blur-md sm:px-6">
      <div className="flex min-w-0 items-center gap-2">
        <button
          type="button"
          onClick={onOpenMobileNav}
          className="-ml-1.5 rounded-md p-2 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100 lg:hidden"
          aria-label="Open navigation"
        >
          <IconMenu className="h-5 w-5" />
        </button>
        <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-2 text-sm">
          <span className="hidden truncate text-zinc-500 sm:inline">{SITE_NAME}</span>
          <span className="hidden text-zinc-700 sm:inline" aria-hidden>
            /
          </span>
          <span className="truncate font-medium text-zinc-100" aria-current="page">
            {pageTitle(pathname)}
          </span>
        </nav>
      </div>

      <div className="flex items-center gap-2">
        <Link
          to="/incidents?status=open"
          onClick={clearUnread}
          className={cn(
            'relative flex h-9 w-9 items-center justify-center rounded-md text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100',
            'focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500',
            bellPulse && 'animate-bell-pulse',
          )}
          aria-label={`Open incidents${unreadAlerts ? `, ${unreadAlerts} new` : ''}`}
          title="Open incidents"
        >
          <IconBell className="h-[18px] w-[18px]" />
          {unreadAlerts > 0 ? (
            <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white ring-2 ring-[#0f1117]">
              {unreadAlerts > 9 ? '9+' : unreadAlerts}
            </span>
          ) : null}
        </Link>
        <span className="mx-1 hidden h-6 w-px bg-zinc-800 sm:block" aria-hidden />
        <UserMenu />
      </div>
    </header>
  )
}

function UserMenu() {
  const { userEmail, fullName, role, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)
  const displayName = fullName || userEmail?.split('@')[0] || 'User'

  useEffect(() => {
    if (!open) return undefined
    const onDown = (e) => {
      if (!rootRef.current?.contains(e.target)) setOpen(false)
    }
    const onKey = (e) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  function go(to) {
    setOpen(false)
    navigate(to)
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex h-9 items-center gap-2 rounded-md py-1 pl-1 pr-2 text-left transition-colors hover:bg-zinc-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500"
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-amber-400/30 to-amber-600/20 text-[11px] font-semibold text-amber-200 ring-1 ring-amber-500/30">
          {initials(displayName)}
        </span>
        <span className="hidden min-w-0 sm:block">
          <span className="block max-w-[160px] truncate text-xs font-medium text-zinc-100">{displayName}</span>
          <span className="block text-[10px] leading-tight text-zinc-500">{ROLE_LABEL[role] ?? 'Loading role…'}</span>
        </span>
        <IconChevronDown className={cn('h-3.5 w-3.5 text-zinc-500 transition-transform', open && 'rotate-180')} />
      </button>

      {open ? (
        <div
          role="menu"
          className="animate-pop-in absolute right-0 mt-2 w-64 overflow-hidden rounded-lg border border-zinc-700/80 bg-[#1a1d27] shadow-2xl shadow-black/50"
        >
          <div className="border-b border-zinc-800 px-3.5 py-3">
            <p className="truncate text-sm font-medium text-zinc-100">{displayName}</p>
            <p className="truncate text-xs text-zinc-500">{userEmail}</p>
            {role ? (
              <span className="mt-2 inline-flex rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-300 ring-1 ring-inset ring-amber-500/30">
                {ROLE_LABEL[role]}
              </span>
            ) : null}
          </div>
          <div className="p-1">
            <MenuItem icon={IconUser} onClick={() => go('/settings?tab=profile')}>
              Profile &amp; password
            </MenuItem>
            <MenuItem icon={IconSettings} onClick={() => go('/settings?tab=notifications')}>
              Notification settings
            </MenuItem>
          </div>
          <div className="border-t border-zinc-800 p-1">
            <MenuItem icon={IconLogout} onClick={logout} danger>
              Sign out
            </MenuItem>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function MenuItem({ icon: Icon, onClick, danger, children }) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-sm transition-colors focus-visible:outline-none',
        danger
          ? 'text-red-300 hover:bg-red-500/10 focus-visible:bg-red-500/10'
          : 'text-zinc-300 hover:bg-zinc-800 hover:text-zinc-50 focus-visible:bg-zinc-800',
      )}
    >
      <Icon className="h-4 w-4" />
      {children}
    </button>
  )
}
