import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/auth/useAuth'
import { Spinner } from '@/components/ui/Spinner'

/**
 * Route guard for the protected /app subtree. While the initial /auth/me
 * bootstrap is in flight we show a spinner; once resolved, unauthenticated
 * visitors are redirected to /login (preserving where they were headed so we
 * can bounce them back after sign-in).
 */
export function RequireAuth() {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-cream">
        <Spinner label="Loading your studio…" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}
