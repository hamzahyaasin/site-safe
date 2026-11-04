import { NavLink } from 'react-router-dom'
import { cn } from '../../lib/utils.js'
import { useAuth } from '../../context/AuthContext.jsx'
import { useWebSocket } from '../../hooks/useWebSocket.js'
import { IconPanelLeft, IconShield, IconX } from '../ui/icons.jsx'
import { NAV_SECTIONS } from './navConfig.js'

const STATUS = {
  live: { label: 'Live updates on', dot: 'bg-emerald-500', ring: 'shadow-[0_0_0_3px_rgba(16,185,129,0.15)]' },
  reconnecting: { label: 'Reconnecting…', dot: 'bg-amber-500 animate-pulse', ring: '' },
  offline: { label: 'Live updates off', dot: 'bg-red-500', ring: '' },
}

/**
 * Primary navigation. On large screens it is fixed at the left and can be
 * collapsed to icons; below that it is an off-canvas panel opened from the
 * top bar (``mobileOpen``).
 */
export default function Sidebar({ collapsed, onToggle, mobileOpen, onCloseMobile, unresolvedCount = 0 }) {
  const { canOperate } = useAuth()
  const { status } = useWebSocket()
  const conn = STATUS[status] || STATUS.offline
  // Collapsing only applies to the docked desktop sidebar.
  const compact = collapsed && !mobileOpen

  return (
    <>
      {mobileOpen ? (
        <div aria-hidden className="animate-fade-in fixed inset-0 z-30 bg-black/60 lg:hidden" onClick={onCloseMobile} />
      ) : null}
      <aside
        aria-label="Main navigation"
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-zinc-800/80 bg-[#101219] transition-[width,transform] duration-200',
          mobileOpen ? 'translate-x-0 shadow-2xl shadow-black/60' : '-translate-x-full lg:translate-x-0',
          compact ? 'lg:w-16' : 'lg:w-60',
        )}
      >
        <div className={cn('flex h-14 shrink-0 items-center gap-2 border-b border-zinc-800/80 px-3', compact && 'lg:justify-center lg:px-0')}>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 text-zinc-950 shadow-sm shadow-amber-900/40">
            <IconShield className="h-4 w-4" strokeWidth={2.25} />
          </div>
          <div className={cn('min-w-0 flex-1', compact && 'lg:hidden')}>
            <p className="truncate text-sm font-semibold tracking-tight text-zinc-50">Site-Safe</p>
            <p className="truncate text-[11px] text-zinc-500">Safety Command</p>
          </div>
          <button
            type="button"
            onClick={onCloseMobile}
            className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100 lg:hidden"
            aria-label="Close navigation"
          >
            <IconX className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-4 scrollbar-thin">
          {NAV_SECTIONS.map((section) => (
            <div key={section.label} className="mb-5 last:mb-0">
              {compact ? (
                <div className="mx-3 mb-2 hidden h-px bg-zinc-800 lg:block" aria-hidden />
              ) : (
                <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-500">
                  {section.label}
                </p>
              )}
              <ul className="space-y-0.5">
                {section.items
                  .filter((item) => !item.operatorsOnly || canOperate)
                  .map((item) => {
                    const badge = item.badgeKey === 'incidents' && unresolvedCount > 0 ? unresolvedCount : 0
                    return (
                      <li key={item.to}>
                        <NavLink
                          to={item.to}
                          end={item.end}
                          onClick={onCloseMobile}
                          title={compact ? item.label : undefined}
                          aria-label={compact ? `${item.label}${badge ? `, ${badge} open` : ''}` : undefined}
                          className={({ isActive }) =>
                            cn(
                              'group relative flex h-9 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors',
                              'focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-amber-500',
                              compact && 'lg:justify-center lg:px-0',
                              isActive
                                ? 'bg-amber-500/10 text-amber-300'
                                : 'text-zinc-400 hover:bg-zinc-800/70 hover:text-zinc-100',
                            )
                          }
                        >
                          {({ isActive }) => (
                            <>
                              {isActive ? (
                                <span aria-hidden className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-amber-400" />
                              ) : null}
                              <item.icon className="h-[18px] w-[18px] shrink-0" />
                              <span className={cn('flex-1 truncate', compact && 'lg:hidden')}>{item.label}</span>
                              {badge ? (
                                compact ? (
                                  <span aria-hidden className="absolute right-2 top-1.5 h-2 w-2 rounded-full bg-red-500 ring-2 ring-[#101219]" />
                                ) : (
                                  <span className="min-w-5 rounded-full bg-red-500/15 px-1.5 py-0.5 text-center text-[10px] font-semibold tabular-nums text-red-300 ring-1 ring-inset ring-red-500/30">
                                    {badge > 99 ? '99+' : badge}
                                  </span>
                                )
                              ) : null}
                            </>
                          )}
                        </NavLink>
                      </li>
                    )
                  })}
              </ul>
            </div>
          ))}
        </nav>

        <div className="shrink-0 space-y-1 border-t border-zinc-800/80 p-2">
          <div
            className={cn('flex h-9 items-center gap-2.5 rounded-md px-3 text-xs text-zinc-400', compact && 'lg:justify-center lg:px-0')}
            title={compact ? conn.label : undefined}
            role="status"
          >
            <span className={cn('h-2 w-2 shrink-0 rounded-full', conn.dot, conn.ring)} aria-hidden />
            <span className={cn(compact && 'lg:sr-only')}>{conn.label}</span>
          </div>
          <button
            type="button"
            onClick={onToggle}
            className={cn(
              'hidden h-9 w-full items-center gap-2.5 rounded-md px-3 text-xs font-medium text-zinc-500 transition-colors hover:bg-zinc-800/70 hover:text-zinc-200 lg:flex',
              compact && 'justify-center px-0',
            )}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={collapsed ? 'Expand sidebar' : undefined}
          >
            <IconPanelLeft className="h-4 w-4 shrink-0" />
            {compact ? null : <span>Collapse</span>}
          </button>
        </div>
      </aside>
    </>
  )
}
