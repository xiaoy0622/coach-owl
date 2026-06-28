import { lazy, Suspense, type ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { RequireAuth } from '@/auth/RequireAuth'
import { AppLayout } from '@/components/AppLayout'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { Spinner } from '@/components/ui'

/**
 * Route table — every screen is URL-addressable (CoachOwl architecture rule).
 *
 *   /                 → redirect to the app
 *   /login            → public sign-in
 *   /register         → public sign-up
 *   /app              → protected shell (RequireAuth)
 *     index           → Dashboard
 *     /students/*     → Students feature sub-router  (Wave 2 — features/students)
 *     /calendar/*     → Scheduling feature sub-router (Wave 2 — features/scheduling)
 *     /payments/*     → Payments feature sub-router   (Wave 2 — features/payments)
 *     /settings       → Org settings (live, PATCH /api/v1/org)
 *   *                 → 404
 *
 * Each Wave-2 domain is mounted as a self-contained sub-router (`<domain>/*`)
 * lazy-loaded from its feature folder. Domain agents own everything inside
 * `features/<domain>/` (including nested routes) and never edit this file.
 */
const StudentsRoutes = lazy(() => import('@/features/students/routes'))
const SchedulingRoutes = lazy(() => import('@/features/scheduling/routes'))
const PaymentsRoutes = lazy(() => import('@/features/payments/routes'))

function Lazy({ children }: { children: ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center p-16">
          <Spinner />
        </div>
      }
    >
      {children}
    </Suspense>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<RequireAuth />}>
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="students/*" element={<Lazy><StudentsRoutes /></Lazy>} />
          <Route path="calendar/*" element={<Lazy><SchedulingRoutes /></Lazy>} />
          <Route path="payments/*" element={<Lazy><PaymentsRoutes /></Lazy>} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
