import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ApiError } from '@/lib/api'
import { useAuth } from '@/auth/useAuth'
import { Button, InlineError, Spinner } from '@/components/ui'
import { schedulingApi } from '@/features/scheduling/api'
import { useCalendarParams } from '@/features/scheduling/useCalendarParams'
import { WeekView } from '@/features/scheduling/components/WeekView'
import { MonthView } from '@/features/scheduling/components/MonthView'
import { LessonForm } from '@/features/scheduling/components/LessonForm'
import { LessonDetail } from '@/features/scheduling/components/LessonDetail'
import {
  addDays,
  addMonths,
  MONTH_LABELS,
  startOfWeek,
  todayInTz,
  zonedWallToUtc,
  type PlainDate,
} from '@/features/scheduling/datetime'
import { findConflictIds } from '@/features/scheduling/datetime'

function rangeFor(view: 'week' | 'month', anchor: PlainDate, tz: string) {
  if (view === 'week') {
    const start = startOfWeek(anchor)
    return {
      from: zonedWallToUtc(start, 0, 0, tz).toISOString(),
      to: zonedWallToUtc(addDays(start, 7), 0, 0, tz).toISOString(),
    }
  }
  const gridStart = startOfWeek({ y: anchor.y, m: anchor.m, d: 1 })
  return {
    from: zonedWallToUtc(gridStart, 0, 0, tz).toISOString(),
    to: zonedWallToUtc(addDays(gridStart, 42), 0, 0, tz).toISOString(),
  }
}

function titleFor(view: 'week' | 'month', anchor: PlainDate): string {
  if (view === 'month') return `${MONTH_LABELS[anchor.m - 1]} ${anchor.y}`
  const start = startOfWeek(anchor)
  const end = addDays(start, 6)
  const sameMonth = start.m === end.m
  const startLabel = `${start.d}${sameMonth ? '' : ' ' + MONTH_LABELS[start.m - 1].slice(0, 3)}`
  return `${startLabel} – ${end.d} ${MONTH_LABELS[end.m - 1].slice(0, 3)} ${end.y}`
}

export default function CalendarPage() {
  const { org } = useAuth()
  const tz = org?.timezone ?? 'Australia/Sydney'
  const {
    view,
    anchor,
    panel,
    slot,
    setView,
    setAnchor,
    openNew,
    openLesson,
    closePanel,
  } = useCalendarParams(tz)

  const { from, to } = useMemo(
    () => rangeFor(view, anchor, tz),
    [view, anchor, tz],
  )

  const query = useQuery({
    queryKey: ['lessons', from, to],
    queryFn: ({ signal }) => schedulingApi.list(from, to, signal),
  })

  const lessons = useMemo(() => query.data?.items ?? [], [query.data])
  const conflicts = useMemo(() => findConflictIds(lessons), [lessons])

  const goPrev = () =>
    setAnchor(
      view === 'week' ? addDays(startOfWeek(anchor), -7) : addMonths(anchor, -1),
    )
  const goNext = () =>
    setAnchor(
      view === 'week' ? addDays(startOfWeek(anchor), 7) : addMonths(anchor, 1),
    )
  const goToday = () => setAnchor(todayInTz(tz))

  return (
    <>
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="font-display text-2xl font-black tracking-[-0.02em] text-ink-deep sm:text-3xl">
            {titleFor(view, anchor)}
          </h1>
          {query.isFetching && <Spinner size="sm" />}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center rounded-xl border border-brand-600/15 bg-white p-0.5">
            <button
              type="button"
              onClick={goPrev}
              aria-label="Previous"
              className="co-focus rounded-lg px-2.5 py-1.5 text-muted hover:bg-brand-50 hover:text-ink-deep"
            >
              ‹
            </button>
            <button
              type="button"
              onClick={goToday}
              className="co-focus rounded-lg px-3 py-1.5 text-sm font-bold text-ink-deep hover:bg-brand-50"
            >
              Today
            </button>
            <button
              type="button"
              onClick={goNext}
              aria-label="Next"
              className="co-focus rounded-lg px-2.5 py-1.5 text-muted hover:bg-brand-50 hover:text-ink-deep"
            >
              ›
            </button>
          </div>

          <div className="flex items-center rounded-xl border border-brand-600/15 bg-white p-0.5">
            {(['week', 'month'] as const).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setView(v)}
                aria-pressed={view === v}
                className={
                  'co-focus rounded-lg px-3 py-1.5 text-sm font-bold capitalize transition-colors ' +
                  (view === v
                    ? 'bg-brand-500 text-white'
                    : 'text-muted hover:bg-brand-50 hover:text-ink-deep')
                }
              >
                {v}
              </button>
            ))}
          </div>

          <Button size="sm" onClick={() => openNew()}>
            + New lesson
          </Button>
        </div>
      </header>

      {query.isError && (
        <InlineError
          message={
            query.error instanceof ApiError
              ? query.error.message
              : 'Could not load your calendar.'
          }
          className="mb-4"
        />
      )}

      {conflicts.size > 0 && (
        <div className="mb-4 rounded-2xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm font-semibold text-danger">
          {conflicts.size} lesson{conflicts.size === 1 ? '' : 's'} overlap another
          for the same coach — outlined in red below.
        </div>
      )}

      {view === 'week' ? (
        <WeekView
          anchor={anchor}
          lessons={lessons}
          tz={tz}
          conflicts={conflicts}
          onOpenLesson={openLesson}
          onCreateAt={(s) => openNew(s)}
        />
      ) : (
        <MonthView
          anchor={anchor}
          lessons={lessons}
          tz={tz}
          conflicts={conflicts}
          onOpenLesson={openLesson}
          onCreateAt={(s) => openNew(s)}
          onPickDay={(day) => {
            setAnchor(day)
            setView('week')
          }}
        />
      )}

      {panel === 'new' && <LessonForm slot={slot} onClose={closePanel} />}
      {panel && panel !== 'new' && (
        <LessonDetail lessonId={panel} onClose={closePanel} />
      )}
    </>
  )
}
