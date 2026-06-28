// Scheduling contract types — mirror api/app/schemas/scheduling.py (camelCase).

export type LessonStatus = 'scheduled' | 'completed' | 'cancelled' | 'no_show'

export type RecurrenceFreq = 'weekly'

export interface RecurrenceRuleCreate {
  freq: RecurrenceFreq
  interval: number
  byweekday: number[] // 0=Mon .. 6=Sun
  startDate: string // YYYY-MM-DD
  endDate?: string | null
  startTime: string // HH:MM:SS
  durationMin: number
}

export interface Lesson {
  id: string
  orgId: string
  studentId: string
  coachId: string
  recurrenceId: string | null
  startsAt: string // ISO8601 UTC
  durationMin: number
  status: LessonStatus
  location: string | null
  meetingUrl: string | null
  cancelReason: string | null
  creditDeducted: boolean
  capacity: number
  createdAt: string
  updatedAt: string
}

export interface LessonCreate {
  studentId: string
  coachId: string
  startsAt: string
  durationMin: number
  status?: LessonStatus
  location?: string | null
  meetingUrl?: string | null
  recurrence?: RecurrenceRuleCreate | null
}

export interface LessonUpdate {
  startsAt?: string
  durationMin?: number
  status?: LessonStatus
  location?: string | null
  meetingUrl?: string | null
  cancelReason?: string | null
  deductCredit?: boolean
}

export interface Page<T> {
  items: T[]
  nextCursor: string | null
}

export interface RecurrencePreview {
  occurrences: string[] // ISO8601 UTC
  count: number
}

/** Shape of one entry in a 409 `lesson_conflict` error's `details`. */
export interface LessonConflictDetail {
  lessonId: string
  coachId: string
  startsAt: string
  durationMin: number
}
