import { Navigate, Route, Routes } from 'react-router-dom'
import LoginPage from './components/auth/LoginPage.jsx'
import DashboardLayout from './components/layout/DashboardLayout.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import IncidentsPage from './pages/IncidentsPage.jsx'
import ReportsPage from './pages/ReportsPage.jsx'
import SettingsPage from './pages/SettingsPage.jsx'
import VestManagementPage from './pages/VestManagementPage.jsx'
import WorkersPage from './pages/WorkersPage.jsx'
import ZonesPage from './pages/ZonesPage.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/workers" element={<WorkersPage />} />
          <Route path="/incidents" element={<IncidentsPage />} />
          <Route path="/alerts" element={<Navigate to="/incidents" replace />} />
          <Route path="/vests" element={<VestManagementPage />} />
          <Route path="/zones" element={<ZonesPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
