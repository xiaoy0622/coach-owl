import { cn } from '@/lib/cn'
import {
  addDays,
  dateStr,
  formatTime,
  localDateStr,
  localMinutes,
  sameDate,
  startOfWeek,
  todayInTz,
  WEEKDAY_LABELS,
  type PlainDate,
} from '@/features/scheduling/datetime'
import { STATUS_CHIP, STATUS_DOT } from '@/features/scheduling/status'
import type { Lesson } from '@/features/scheduling/types'

const START_HOUR = 6
const END_HOUR = 22
const HOUR_PX = 52
const TOTAL_MIN = (END_HOUR - START_HOUR) * 60

function clampTop(minutes: number): number {
  const m = Math.min(Math.max(minutes - START_HOUR * 60, 0), TOTAL_MIN)
  return (m / 60) * HOUR_PX
}

export function WeekView({
  anchor,
  lessons,
  tz,
  conflicts,
  onOpenLesson,
  onCreateAt,
}: {
  anchor: PlainDate
  lessons: Lesson[]
  tz: string
  conflicts: Set<string>
  onOpenLesson: (id: string) => void
  onCreateAt: (slot: string) => void
}) {
  const weekStart = startOfWeek(anchor)
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i))
  const today = todayInTz(tz)
  const hours = Array.from(
    { length: END_HOUR - START_HOUR + 1 },
    (_, i) => START_HOUR + i,
  )

  const byDay = new Map<string, Lesson[]>()
  for (const lesson of lessons) {
    const key = localDateStr(lesson.startsAt, tz)
    const arr = byDay.get(key)
    if (arr) arr.push(lesson)
    else byDay.set(key, [lesson])
  }

  return (
    <div className="overflow-x-auto rounded-3xl border border-brand-600/10 bg-white shadow-card">
      <div className="min-w-[720px]">
        {/* Day headers */}
        <div className="grid grid-cols-[3.5rem_repeat(7,1fr)] border-b border-brand-600/10">
          <div />
          {days.map((day, i) => {
            const isToday = sameDate(day, today)
            return (
              <div
                key={dateStr(day)}
                className="border-l border-brand-600/10 px-2 py-2.5 text-center"
              >
                <div className="text-[11px] font-bold uppercase tracking-wide text-muted">
                  {WEEKDAY_LABELS[i]}
                </div>
                <div
                  className={cn(
                    'mx-auto mt-0.5 flex h-7 w-7 items-center justify-center rounded-full font-display text-sm font-black',
                    isToday ? 'bg-brand-500 text-white' : 'text-ink-deep',
                  )}
                >
                  {day.d}
                </div>
              </div>
            )
          })}
        </div>

        {/* Time grid */}
        <div className="grid grid-cols-[3.5rem_repeat(7,1fr)]">
          {/* hour gutter */}
          <div className="relative" style={{ height: TOTAL_MIN / 60 * HOUR_PX }}>
            {hours.map((h) => (
              <div
                key={h}
                className="absolute right-2 -translate-y-1/2 text-[11px] font-semibold text-muted"
                style={{ top: (h - START_HOUR) * HOUR_PX }}
              >
                {h % 12 === 0 ? 12 : h % 12}
                {h < 12 ? 'a' : 'p'}
              </div>
            ))}
          </div>

          {days.map((day) => {
            const key = dateStr(day)
            const dayLessons = byDay.get(key) ?? []
            return (
              <div
                key={key}
                className="relative border-l border-brand-600/10"
                style={{ height: (TOTAL_MIN / 60) * HOUR_PX }}
              >
                {/* hour lines + click-to-create slots */}
                {hours.slice(0, -1).map((h) => (
                  <button
                    key={h}
                    type="button"
                    aria-label={`Add lesson on ${key} at ${h}:00`}
                    onClick={() =>
                      onCreateAt(`${key}T${String(h).padStart(2, '0')}:00`)
                    }
                    className="co-focus absolute left-0 right-0 border-t border-brand-600/[0.06] hover:bg-brand-50/70"
                    style={{ top: (h - START_HOUR) * HOUR_PX, height: HOUR_PX }}
                  />
                ))}

                {/* lessons */}
                {dayLessons.map((lesson) => {
                  const top = clampTop(localMinutes(lesson.startsAt, tz))
                  const height = Math.max(
                    18,
                    (lesson.durationMin / 60) * HOUR_PX - 2,
                  )
                  const conflicted = conflicts.has(lesson.id)
                  return (
                    <button
                      key={lesson.id}
                      type="button"
                      onClick={() => onOpenLesson(lesson.id)}
                      title={conflicted ? 'Time conflict for this coach' : undefined}
                      className={cn(
                        'co-focus absolute left-1 right-1 overflow-hidden rounded-lg border px-1.5 py-1 text-left text-[11px] font-semibold leading-tight shadow-sm transition-shadow hover:shadow-md',
                        STATUS_CHIP[lesson.status],
                        conflicted && 'ring-2 ring-danger/70',
                      )}
                      style={{ top, height }}
                    >
                      <span className="flex items-center gap-1">
                        <span
                          className={cn(
                            'h-1.5 w-1.5 shrink-0 rounded-full',
                            STATUS_DOT[lesson.status],
                          )}
                          aria-hidden="true"
                        />
                        {formatTime(lesson.startsAt, tz)}
                        {conflicted && (
                          <span className="ml-auto text-danger" aria-hidden="true">
                            !
                          </span>
                        )}
                      </span>
                    </button>
                  )
                })}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
