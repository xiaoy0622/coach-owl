import { api } from '@/lib/api'
import type {
  LessonNote,
  LessonNoteCreate,
  LessonNoteUpdate,
  NotesListParams,
  Page,
  StructuredNote,
} from './types'

function qs(params: NotesListParams): string {
  const sp = new URLSearchParams()
  if (params.studentId) sp.set('studentId', params.studentId)
  if (params.lessonId) sp.set('lessonId', params.lessonId)
  if (params.cursor) sp.set('cursor', params.cursor)
  if (params.limit) sp.set('limit', String(params.limit))
  const s = sp.toString()
  return s ? `?${s}` : ''
}

export const notesApi = {
  /** AI candidate only — the backend persists nothing here (confirm-before-save). */
  structure: (rawInput: string) =>
    api.post<StructuredNote>('/api/v1/lesson-notes/structure', { rawInput }),

  list: (params: NotesListParams = {}) =>
    api.get<Page<LessonNote>>(`/api/v1/lesson-notes${qs(params)}`),

  get: (id: string) => api.get<LessonNote>(`/api/v1/lesson-notes/${id}`),

  create: (body: LessonNoteCreate) =>
    api.post<LessonNote>('/api/v1/lesson-notes', body),

  update: (id: string, body: LessonNoteUpdate) =>
    api.patch<LessonNote>(`/api/v1/lesson-notes/${id}`, body),

  remove: (id: string) => api.delete<void>(`/api/v1/lesson-notes/${id}`),
}
