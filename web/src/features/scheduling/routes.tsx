import { Route, Routes } from 'react-router-dom'
import CalendarPage from '@/features/scheduling/CalendarPage'

/**
 * Scheduling feature sub-router — mounted at /app/calendar/* (see App.tsx).
 *
 * The calendar is a single URL-addressable screen whose week/month view and
 * anchor date live in the query string (`/app/calendar?view=week&date=2026-05-12`),
 * so it is deep-linkable and refresh-safe. The create form and per-lesson detail
 * are also driven from the URL via `?panel=new|<lessonId>` (+ optional `?slot=`).
 */
export default function SchedulingRoutes() {
  return (
    <Routes>
      <Route index element={<CalendarPage />} />
    </Routes>
  )
}
