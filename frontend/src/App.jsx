import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import AlertsPage from './pages/AlertsPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
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
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/workers" element={<WorkersPage />} />
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
