import { Route, Routes } from 'react-router-dom'
import { ComingSoonPage } from '@/pages/ComingSoonPage'

/**
 * Scheduling feature sub-router — mounted at /app/calendar/* (see App.tsx).
 *
 * Wave 2 (Scheduling agent) owns this entire folder. Replace this stub with the
 * real calendar: week/month views (read the view + date from the URL, e.g.
 * `/app/calendar?view=week&date=2026-05-12`), single + recurring lessons, and
 * reschedule/cancel. Use the `api` client + TanStack Query.
 */
export default function SchedulingRoutes() {
  return (
    <Routes>
      <Route
        index
        element={
          <ComingSoonPage
            title="Calendar"
            description="Weekly and monthly views of every lesson."
            blurb="Recurring lessons, drag-to-reschedule and conflict detection are coming next. Set a weekly slot once and CoachOwl keeps everyone in sync."
          />
        }
      />
    </Routes>
  )
}
