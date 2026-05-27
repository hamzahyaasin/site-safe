import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

function IconGrid() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
    </svg>
  )
}

function IconBell() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  )
}

function IconUsers() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  )
}

function IconLogout() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  )
}

function navClass({ isActive }) {
  return isActive ? 'sidebar__nav-link sidebar__nav-link--active' : 'sidebar__nav-link'
}

export default function Sidebar({ alertCount = 0 }) {
  const { userEmail, logout } = useAuth()

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__logo-row">
          <div className="sidebar__icon">⛑️</div>
          <span className="sidebar__name">Site-Safe</span>
        </div>
        <span className="sidebar__tagline">Construction Safety</span>
      </div>

      <nav className="sidebar__nav">
        <span className="sidebar__section-label">Navigation</span>

        <NavLink to="/" end className={navClass}>
          <span className="sidebar__nav-icon">
            <IconGrid />
          </span>
          <span className="sidebar__nav-label">Dashboard</span>
        </NavLink>

        <NavLink to="/alerts" className={navClass}>
          <span className="sidebar__nav-icon">
            <IconBell />
          </span>
          <span className="sidebar__nav-label">Alerts</span>
          {alertCount > 0 && (
            <span className="sidebar__alert-badge">{alertCount > 99 ? '99+' : alertCount}</span>
          )}
        </NavLink>

        <NavLink to="/workers" className={navClass}>
          <span className="sidebar__nav-icon">
            <IconUsers />
          </span>
          <span className="sidebar__nav-label">Workers</span>
        </NavLink>
      </nav>

      <div className="sidebar__divider" />

      <div className="sidebar__status-block">
        <span className="sidebar__status-dot" />
        <span className="sidebar__status-text">AI Monitor Active</span>
      </div>

      <div className="sidebar__user">
        <span className="sidebar__user-email" title={userEmail || ''}>
          {userEmail || '—'}
        </span>
        <button type="button" className="sidebar__logout" onClick={logout}>
          <IconLogout />
          Sign out
        </button>
      </div>
    </aside>
  )
}
