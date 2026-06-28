import type { LessonStatus } from '@/features/scheduling/types'

export const STATUS_LABEL: Record<LessonStatus, string> = {
  scheduled: 'Scheduled',
  completed: 'Completed',
  cancelled: 'Cancelled',
  no_show: 'No-show',
}

/** Chip styles per status (calm CoachOwl palette). */
export const STATUS_CHIP: Record<LessonStatus, string> = {
  scheduled: 'bg-brand-100 text-brand-700 border-brand-600/20',
  completed: 'bg-emerald-50 text-emerald-700 border-emerald-600/20',
  cancelled: 'bg-stone-100 text-stone-500 border-stone-300 line-through',
  no_show: 'bg-amber-50 text-amber-700 border-amber-500/30',
}

export const STATUS_DOT: Record<LessonStatus, string> = {
  scheduled: 'bg-brand-500',
  completed: 'bg-emerald-500',
  cancelled: 'bg-stone-400',
  no_show: 'bg-amber-500',
}
