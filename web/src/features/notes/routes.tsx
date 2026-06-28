import { Route, Routes } from 'react-router-dom'
import { NotesTimelinePage } from './pages/NotesTimelinePage'
import { NoteCapturePage } from './pages/NoteCapturePage'
import { NoteDetailPage } from './pages/NoteDetailPage'

/**
 * Notes feature sub-router — mounted at /app/notes/* (see App.tsx).
 * Every screen is URL-addressable and refresh-safe (state loads from the route).
 *
 *   /app/notes                 progress-note timeline (filter via ?student=<id>)
 *   /app/notes/new             capture flow: jot → AI structure → confirm → save
 *   /app/notes/:id             view / re-edit / delete a saved note
 *
 * AI output is only ever a candidate — the coach confirms/edits before it is
 * persisted (CoachOwl-Execution-Plan §1.4 铁律).
 */
export default function NotesRoutes() {
  return (
    <Routes>
      <Route index element={<NotesTimelinePage />} />
      <Route path="new" element={<NoteCapturePage />} />
      <Route path=":id" element={<NoteDetailPage />} />
    </Routes>
  )
}
