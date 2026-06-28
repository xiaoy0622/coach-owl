import { Navigate, Route, Routes } from 'react-router-dom'
import { RequireAuth } from '@/auth/RequireAuth'
import { AppLayout } from '@/components/AppLayout'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import {
  CalendarPage,
  PaymentsPage,
  StudentsPage,
} from '@/pages/domain-pages'

/**
 * Route table — every screen is URL-addressable (CoachOwl architecture rule).
 *
 *   /                 → redirect to the app
 *   /login            → public sign-in
 *   /register         → public sign-up
 *   /app              → protected shell (RequireAuth)
 *     index           → Dashboard
 *     /students       → Students (Wave 2)
 *     /calendar       → Calendar (Wave 2)
 *     /payments       → Payments (Wave 2)
 *     /settings       → Org settings (live, PATCH /api/v1/org)
 *   *                 → 404
 */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<RequireAuth />}>
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="students" element={<StudentsPage />} />
          <Route path="calendar" element={<CalendarPage />} />
          <Route path="payments" element={<PaymentsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
