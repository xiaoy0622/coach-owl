// Lesson-notes contract types (mirror api/app/schemas/lesson_notes.py).
// Response keys are camelCase (see Execution-Plan §5).

export type NoteSource = 'text' | 'voice'

export interface StructuredNote {
  topics: string[]
  progress: string | null
  homework: string | null
}

export interface LessonNote {
  id: string
  orgId: string
  lessonId: string
  studentId: string
  rawInput: string | null
  structured: StructuredNote
  source: NoteSource
  audioUrl: string | null
  createdAt: string
}

export interface LessonNoteCreate {
  lessonId: string
  studentId: string
  rawInput?: string | null
  structured: StructuredNote
  source?: NoteSource
  audioUrl?: string | null
}

export interface LessonNoteUpdate {
  rawInput?: string | null
  structured?: StructuredNote
  source?: NoteSource
  audioUrl?: string | null
}

export interface NotesListParams {
  studentId?: string
  lessonId?: string
  cursor?: string
  limit?: number
}

export interface Page<T> {
  items: T[]
  nextCursor: string | null
}
