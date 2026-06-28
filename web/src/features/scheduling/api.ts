import { api } from '@/lib/api'
import type {
  Lesson,
  LessonCreate,
  LessonUpdate,
  Page,
  RecurrencePreview,
  RecurrenceRuleCreate,
} from '@/features/scheduling/types'

export const schedulingApi = {
  /** GET /api/v1/lessons?from&to — lessons overlapping the window. */
  list: (fromIso: string, toIso: string, signal?: AbortSignal) => {
    const qs = new URLSearchParams({ from: fromIso, to: toIso }).toString()
    return api.get<Page<Lesson>>(`/api/v1/lessons?${qs}`, { signal })
  },

  /** POST /api/v1/lessons — single or recurring (returns the created set). */
  create: (body: LessonCreate) =>
    api.post<Page<Lesson>>('/api/v1/lessons', body),

  get: (id: string, signal?: AbortSignal) =>
    api.get<Lesson>(`/api/v1/lessons/${id}`, { signal }),

  /** PATCH /api/v1/lessons/:id — reschedule / cancel / no_show / complete. */
  update: (id: string, body: LessonUpdate) =>
    api.patch<Lesson>(`/api/v1/lessons/${id}`, body),

  /** POST /api/v1/lessons/recurrence/preview — expand a rule to UTC times. */
  previewRecurrence: (recurrence: RecurrenceRuleCreate, limit = 100) =>
    api.post<RecurrencePreview>('/api/v1/lessons/recurrence/preview', {
      recurrence,
      limit,
    }),
}
