import { Route, Routes } from 'react-router-dom'
import { ComingSoonPage } from '@/pages/ComingSoonPage'

/**
 * Students feature sub-router — mounted at /app/students/* (see App.tsx).
 *
 * Wave 2 (Students agent) owns this entire folder. Replace this stub with the
 * real feature: an index roster list + a `:id` profile route, e.g.
 *   <Route index element={<StudentListPage />} />
 *   <Route path=":id" element={<StudentProfilePage />} />
 * Use the `api` client + TanStack Query; keep every screen URL-addressable.
 */
export default function StudentsRoutes() {
  return (
    <Routes>
      <Route
        index
        element={
          <ComingSoonPage
            title="Students"
            description="Your roster — names, subjects, contacts and credits."
            blurb="Smart Import and student profiles are on the way. Soon you'll add students, track their lesson credits, and keep guardian details tidy — all in one calm list."
          />
        }
      />
    </Routes>
  )
}
