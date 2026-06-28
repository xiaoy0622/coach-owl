import { cn } from '@/lib/cn'
import { formatTime } from '@/features/scheduling/datetime'
import { STATUS_CHIP, STATUS_DOT } from '@/features/scheduling/status'
import type { Lesson } from '@/features/scheduling/types'

/** A compact lesson chip used in the month grid + week all-day fallback. */
export function LessonChip({
  lesson,
  tz,
  conflicted,
  onClick,
}: {
  lesson: Lesson
  tz: string
  conflicted?: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={conflicted ? 'Time conflict for this coach' : undefined}
      className={cn(
        'co-focus group flex w-full items-center gap-1.5 truncate rounded-lg border px-2 py-1 text-left text-xs font-semibold transition-colors',
        STATUS_CHIP[lesson.status],
        conflicted && 'ring-2 ring-danger/70 ring-offset-1',
      )}
    >
      <span
        className={cn('h-1.5 w-1.5 shrink-0 rounded-full', STATUS_DOT[lesson.status])}
        aria-hidden="true"
      />
      <span className="truncate">{formatTime(lesson.startsAt, tz)}</span>
      {conflicted && <span className="ml-auto text-danger" aria-hidden="true">!</span>}
    </button>
  )
}
