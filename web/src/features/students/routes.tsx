import { Route, Routes } from 'react-router-dom'
import { StudentListPage } from './pages/StudentListPage'
import { StudentNewPage } from './pages/StudentNewPage'
import { StudentEditPage } from './pages/StudentEditPage'
import { StudentProfilePage } from './pages/StudentProfilePage'
import { ImportPage } from './pages/ImportPage'
import { ImportReviewPage } from './pages/ImportReviewPage'

/**
 * Students feature sub-router — mounted at /app/students/* (see App.tsx).
 * Every screen is URL-addressable and refresh-safe (state loads from the route).
 *
 *   /app/students                  roster list (search / status / tag filters)
 *   /app/students/new              add-student form
 *   /app/students/import           Smart Import — paste / upload
 *   /app/students/import/:jobId    review + edit candidates, then commit
 *   /app/students/:id              student profile (details, guardians, notes)
 *   /app/students/:id/edit         edit-student form
 */
export default function StudentsRoutes() {
  return (
    <Routes>
      <Route index element={<StudentListPage />} />
      <Route path="new" element={<StudentNewPage />} />
      <Route path="import" element={<ImportPage />} />
      <Route path="import/:jobId" element={<ImportReviewPage />} />
      <Route path=":id" element={<StudentProfilePage />} />
      <Route path=":id/edit" element={<StudentEditPage />} />
    </Routes>
  )
}
