import { Navigate, Route, Routes } from 'react-router-dom'
import LoginPage from './components/auth/LoginPage.jsx'
import DashboardLayout from './components/layout/DashboardLayout.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import IncidentsPage from './pages/IncidentsPage.jsx'
import StubPage from './pages/StubPage.jsx'
import VestManagementPage from './pages/VestManagementPage.jsx'
import WorkersPage from './pages/WorkersPage.jsx'

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
          <Route
            path="/zones"
            element={
              <StubPage
                title="Zones"
                description="Define and monitor safety zones across the construction site."
              />
            }
          />
          <Route
            path="/reports"
            element={
              <StubPage
                title="Reports"
                description="Generate compliance and incident reports for site audits."
              />
            }
          />
          <Route
            path="/settings"
            element={
              <StubPage
                title="Settings"
                description="Configure alerts, users, and site preferences."
              />
            }
          />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
