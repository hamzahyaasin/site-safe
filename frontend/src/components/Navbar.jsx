import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function Navbar() {
  const { userEmail, logout } = useAuth()

  return (
    <header className="navbar">
      <div className="navbar__brand">
        <span className="navbar__logo">Site-Safe</span>
        <span className="navbar__tag">Construction Safety</span>
      </div>
      <nav className="navbar__links">
        <NavLink to="/" end className={({ isActive }) => (isActive ? 'nav-link nav-link--active' : 'nav-link')}>
          Dashboard
        </NavLink>
        <NavLink to="/alerts" className={({ isActive }) => (isActive ? 'nav-link nav-link--active' : 'nav-link')}>
          Alerts
        </NavLink>
        <NavLink to="/workers" className={({ isActive }) => (isActive ? 'nav-link nav-link--active' : 'nav-link')}>
          Workers
        </NavLink>
        <NavLink to="/vests" className={({ isActive }) => (isActive ? 'nav-link nav-link--active' : 'nav-link')}>
          Vests
        </NavLink>
        <NavLink to="/zones" className={({ isActive }) => (isActive ? 'nav-link nav-link--active' : 'nav-link')}>
          Zones
        </NavLink>
        <NavLink to="/reports" className={({ isActive }) => (isActive ? 'nav-link nav-link--active' : 'nav-link')}>
          Reports
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => (isActive ? 'nav-link nav-link--active' : 'nav-link')}>
          Settings
        </NavLink>
      </nav>
      <div className="navbar__user">
        <span className="navbar__email" title={userEmail || ''}>
          {userEmail || '—'}
        </span>
        <button type="button" className="btn btn--ghost" onClick={logout}>
          Logout
        </button>
      </div>
    </header>
  )
}
