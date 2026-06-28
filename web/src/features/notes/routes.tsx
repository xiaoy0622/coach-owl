import { Route, Routes } from 'react-router-dom'
import { ComingSoonPage } from '@/pages/ComingSoonPage'

/**
 * Notes feature sub-router — mounted at /app/notes/* (see App.tsx).
 *
 * Wave 3 (AI lesson notes agent) owns this entire folder. Replace this stub
 * with the real feature: a per-student/lesson notes timeline and the
 * "jot/speak → structured summary" capture flow (confirm-before-save).
 * Use the api client + TanStack Query; keep every screen URL-addressable.
 */
export default function NotesRoutes() {
  return (
    <Routes>
      <Route
        index
        element={
          <ComingSoonPage
            title="Lesson notes"
            description="Quick notes after class, tidied into progress summaries."
            blurb="Jot a few words or speak after a lesson and CoachOwl turns it into a clean, shareable progress note — tracked across lessons for every student."
          />
        }
      />
    </Routes>
  )
}
