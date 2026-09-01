import { NavLink } from 'react-router-dom'
import { cn } from '../../lib/utils.js'
import { useAuth } from '../../context/AuthContext.jsx'
import { useWebSocket } from '../../hooks/useWebSocket.js'
import Button from '../ui/Button.jsx'

const NAV_SECTIONS = [
  {
    label: 'Overview',
    items: [{ to: '/', label: 'Dashboard', icon: IconGrid, end: true }],
  },
  {
    label: 'Operations',
    items: [
      { to: '/workers', label: 'Workers', icon: IconUsers },
      { to: '/incidents', label: 'Incidents', icon: IconAlertTriangle, badgeKey: 'incidents' },
      { to: '/vests', label: 'Vest Management', icon: IconVest },
    ],
  },
  {
    label: 'Site',
    items: [
      { to: '/zones', label: 'Zones', icon: IconMap },
      { to: '/reports', label: 'Reports', icon: IconChart },
      { to: '/settings', label: 'Settings', icon: IconSettings },
    ],
  },
]

function navLinkClass({ isActive }, disabled) {
  if (disabled) {
    return cn(
      'group flex items-center gap-3 rounded-md px-2.5 py-2 text-sm font-medium opacity-40 pointer-events-none',
      'text-zinc-500',
    )
  }
  return cn(
    'group flex items-center gap-3 rounded-md px-2.5 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500',
    isActive
      ? 'bg-zinc-800 text-amber-400'
      : 'text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200',
  )
}

export default function Sidebar({ collapsed, onToggle, unresolvedCount = 0 }) {
  const { userEmail, logout } = useAuth()
  const { status } = useWebSocket()

  const statusLabel =
    status === 'live' ? 'Live' : status === 'reconnecting' ? 'Reconnecting…' : 'Offline'
  const statusDot =
    status === 'live'
      ? 'bg-emerald-500'
      : status === 'reconnecting'
        ? 'bg-amber-500 animate-pulse'
        : 'bg-red-500'

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-30 flex flex-col border-r border-zinc-800 bg-[#12141c] transition-[width] duration-200',
        collapsed ? 'w-16' : 'w-60',
      )}
    >
      <div className="flex h-14 items-center justify-between border-b border-zinc-800 px-3">
        {!collapsed ? (
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-amber-500/15 text-amber-400">
              <IconShield className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-zinc-100">Site-Safe</p>
              <p className="truncate text-[10px] text-zinc-500">Safety Command</p>
            </div>
          </div>
        ) : (
          <div className="mx-auto flex h-8 w-8 items-center justify-center rounded-md bg-amber-500/15 text-amber-400">
            <IconShield className="h-4 w-4" />
          </div>
        )}
        <button
          type="button"
          onClick={onToggle}
          className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <IconChevron className={cn('h-4 w-4 transition-transform', collapsed && 'rotate-180')} />
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3 scrollbar-thin">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} className="mb-4">
            {!collapsed ? (
              <p className="mb-1.5 px-2.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-600">
                {section.label}
              </p>
            ) : null}
            <ul className="space-y-0.5">
              {section.items.map((item) => (
                <li key={item.to}>
                  {item.disabled ? (
                    <span className={navLinkClass({ isActive: false }, true)}>
                      <item.icon className="h-4 w-4 shrink-0" />
                      {!collapsed ? <span className="flex-1 truncate">{item.label}</span> : null}
                    </span>
                  ) : (
                    <NavLink to={item.to} end={item.end} className={(props) => navLinkClass(props, false)}>
                      <item.icon className="h-4 w-4 shrink-0" />
                      {!collapsed ? (
                        <>
                          <span className="flex-1 truncate">{item.label}</span>
                          {item.badgeKey === 'incidents' && unresolvedCount > 0 ? (
                            <span className="rounded-full bg-red-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-red-400">
                              {unresolvedCount > 99 ? '99+' : unresolvedCount}
                            </span>
                          ) : null}
                        </>
                      ) : null}
                    </NavLink>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-zinc-800 p-2">
        <div
          className={cn(
            'mb-2 flex items-center gap-2 rounded-md border border-zinc-800 bg-zinc-900/50 px-2.5 py-2',
            collapsed && 'justify-center px-0',
          )}
        >
          <span className={cn('h-2 w-2 shrink-0 rounded-full', statusDot)} aria-hidden />
          {!collapsed ? (
            <span className="text-xs text-zinc-400">{statusLabel}</span>
          ) : null}
        </div>

        {!collapsed ? (
          <div className="space-y-2 px-1">
            <p className="truncate text-xs text-zinc-500" title={userEmail || ''}>
              {userEmail || '—'}
            </p>
            <Button variant="ghost" size="sm" className="w-full justify-start" onClick={logout}>
              <IconLogout className="h-3.5 w-3.5" />
              Sign out
            </Button>
          </div>
        ) : (
          <button
            type="button"
            onClick={logout}
            className="mx-auto flex h-8 w-8 items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300"
            aria-label="Sign out"
          >
            <IconLogout className="h-4 w-4" />
          </button>
        )}
      </div>
    </aside>
  )
}

function IconShield({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  )
}

function IconChevron({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  )
}

function IconGrid({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
    </svg>
  )
}

function IconUsers({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  )
}

function IconAlertTriangle({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10.29 3.86L1.82 18h20.36L13.71 3.86 10.29 3.86z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  )
}

function IconVest({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2l3 4h4l-1 14H6L5 6h4l3-4z" />
    </svg>
  )
}

function IconMap({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
    </svg>
  )
}

function IconChart({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  )
}

function IconSettings({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  )
}

function IconLogout({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  )
}
