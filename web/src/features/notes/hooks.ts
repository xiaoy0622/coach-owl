import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { studentsApi } from '@/features/students/api'
import { schedulingApi } from '@/features/scheduling/api'
import { notesApi } from './api'
import type { LessonNoteCreate, LessonNoteUpdate, NotesListParams } from './types'

export const noteKeys = {
  all: ['lesson-notes'] as const,
  list: (params: NotesListParams) => ['lesson-notes', 'list', params] as const,
  detail: (id: string) => ['lesson-notes', 'detail', id] as const,
}

export function useNotes(params: NotesListParams) {
  return useInfiniteQuery({
    queryKey: noteKeys.list(params),
    queryFn: ({ pageParam }: { pageParam: string | undefined }) =>
      notesApi.list({ ...params, cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
  })
}

export function useNote(id: string) {
  return useQuery({
    queryKey: noteKeys.detail(id),
    queryFn: () => notesApi.get(id),
    enabled: Boolean(id),
  })
}

/** Run the AI structurer over a raw jot — returns a candidate, saves nothing. */
export function useStructureNote() {
  return useMutation({
    mutationFn: (rawInput: string) => notesApi.structure(rawInput),
  })
}

export function useCreateNote() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: LessonNoteCreate) => notesApi.create(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: noteKeys.all }),
  })
}

export function useUpdateNote(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: LessonNoteUpdate) => notesApi.update(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: noteKeys.all })
      qc.invalidateQueries({ queryKey: noteKeys.detail(id) })
    },
  })
}

export function useDeleteNote() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => notesApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: noteKeys.all }),
  })
}

// --- Cross-feature reads (for the student / lesson pickers) -----------------
// We only read from the students + scheduling APIs; we never mutate them.

/** All students (first page) — for the timeline filter + capture picker. */
export function useStudentOptions() {
  return useQuery({
    queryKey: ['notes', 'student-options'],
    queryFn: () => studentsApi.list({ limit: 200 }),
  })
}

/**
 * Recent + upcoming lessons, so the coach can attach a note to the lesson it
 * belongs to. Lessons list only by date window, so we pull a generous span and
 * the picker filters to the chosen student client-side.
 */
export function useRecentLessons() {
  return useQuery({
    queryKey: ['notes', 'recent-lessons'],
    queryFn: () => {
      const now = Date.now()
      const from = new Date(now - 120 * 24 * 3600 * 1000).toISOString()
      const to = new Date(now + 14 * 24 * 3600 * 1000).toISOString()
      return schedulingApi.list(from, to)
    },
  })
}
