import { cn } from '@/lib/cn'
import {
  addDays,
  dateStr,
  localDateStr,
  sameDate,
  startOfWeek,
  todayInTz,
  WEEKDAY_LABELS,
  type PlainDate,
} from '@/features/scheduling/datetime'
import { LessonChip } from '@/features/scheduling/components/LessonChip'
import type { Lesson } from '@/features/scheduling/types'

const MAX_CHIPS = 3

export function MonthView({
  anchor,
  lessons,
  tz,
  conflicts,
  onOpenLesson,
  onCreateAt,
  onPickDay,
}: {
  anchor: PlainDate
  lessons: Lesson[]
  tz: string
  conflicts: Set<string>
  onOpenLesson: (id: string) => void
  onCreateAt: (slot: string) => void
  onPickDay: (day: PlainDate) => void
}) {
  // 6 weeks starting from the Monday on/before the 1st of the anchor month.
  const firstOfMonth: PlainDate = { y: anchor.y, m: anchor.m, d: 1 }
  const gridStart = startOfWeek(firstOfMonth)
  const cells = Array.from({ length: 42 }, (_, i) => addDays(gridStart, i))
  const today = todayInTz(tz)

  const byDay = new Map<string, Lesson[]>()
  for (const lesson of lessons) {
    const key = localDateStr(lesson.startsAt, tz)
    const arr = byDay.get(key)
    if (arr) arr.push(lesson)
    else byDay.set(key, [lesson])
  }

  return (
    <div className="overflow-hidden rounded-3xl border border-brand-600/10 bg-white shadow-card">
      <div className="grid grid-cols-7 border-b border-brand-600/10 bg-brand-50/40">
        {WEEKDAY_LABELS.map((label) => (
          <div
            key={label}
            className="px-2 py-2 text-center text-[11px] font-bold uppercase tracking-wide text-muted"
          >
            {label}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7">
        {cells.map((day) => {
          const key = dateStr(day)
          const inMonth = day.m === anchor.m
          const isToday = sameDate(day, today)
          const dayLessons = (byDay.get(key) ?? []).sort((a, b) =>
            a.startsAt < b.startsAt ? -1 : 1,
          )
          const extra = dayLessons.length - MAX_CHIPS
          return (
            <div
              key={key}
              className={cn(
                'min-h-[104px] border-b border-l border-brand-600/[0.08] p-1.5',
                !inMonth && 'bg-stone-50/60',
              )}
            >
              <div className="mb-1 flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => onPickDay(day)}
                  className={cn(
                    'co-focus flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold transition-colors hover:bg-brand-100',
                    isToday && 'bg-brand-500 text-white hover:bg-brand-600',
                    !inMonth && !isToday && 'text-muted',
                    inMonth && !isToday && 'text-ink-deep',
                  )}
                  title="Open this day in week view"
                >
                  {day.d}
                </button>
                <button
                  type="button"
                  aria-label={`Add lesson on ${key}`}
                  onClick={() => onCreateAt(`${key}T09:00`)}
                  className="co-focus rounded-md px-1 text-muted opacity-0 transition-opacity hover:bg-brand-100 hover:text-brand-700 focus-visible:opacity-100 group-hover:opacity-100"
                >
                  +
                </button>
              </div>

              <div className="flex flex-col gap-1">
                {dayLessons.slice(0, MAX_CHIPS).map((lesson) => (
                  <LessonChip
                    key={lesson.id}
                    lesson={lesson}
                    tz={tz}
                    conflicted={conflicts.has(lesson.id)}
                    onClick={() => onOpenLesson(lesson.id)}
                  />
                ))}
                {extra > 0 && (
                  <button
                    type="button"
                    onClick={() => onPickDay(day)}
                    className="co-focus rounded-md px-1 text-left text-[11px] font-bold text-muted hover:text-brand-700"
                  >
                    +{extra} more
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
