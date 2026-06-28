import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  dateStr,
  parseDateStr,
  todayInTz,
  type PlainDate,
} from '@/features/scheduling/datetime'

export type CalendarView = 'week' | 'month'

/**
 * The calendar's navigational state lives entirely in the URL
 * (`/app/calendar?view=week&date=2026-05-12&panel=new|<lessonId>`), so the view
 * is deep-linkable and refresh-safe. This hook reads it and returns setters
 * that push new query strings.
 */
export function useCalendarParams(tz: string) {
  const [params, setParams] = useSearchParams()

  const view: CalendarView = params.get('view') === 'month' ? 'month' : 'week'

  const anchor: PlainDate = useMemo(() => {
    const raw = params.get('date')
    if (raw && /^\d{4}-\d{2}-\d{2}$/.test(raw)) {
      const p = parseDateStr(raw)
      if (!Number.isNaN(p.y) && !Number.isNaN(p.m) && !Number.isNaN(p.d)) {
        return p
      }
    }
    return todayInTz(tz)
  }, [params, tz])

  // `panel` drives the side sheet: 'new' (create form) or a lesson id (detail).
  const panel = params.get('panel')
  // optional prefill for the new-lesson form: ?slot=2026-05-12T16:00
  const slot = params.get('slot')

  const update = useCallback(
    (next: Record<string, string | null>) => {
      setParams(
        (prev) => {
          const merged = new URLSearchParams(prev)
          for (const [k, v] of Object.entries(next)) {
            if (v === null) merged.delete(k)
            else merged.set(k, v)
          }
          return merged
        },
        { replace: false },
      )
    },
    [setParams],
  )

  const setView = useCallback(
    (v: CalendarView) => update({ view: v }),
    [update],
  )
  const setAnchor = useCallback(
    (p: PlainDate) => update({ date: dateStr(p) }),
    [update],
  )
  const openNew = useCallback(
    (slotValue?: string) =>
      update({ panel: 'new', slot: slotValue ?? null }),
    [update],
  )
  const openLesson = useCallback(
    (id: string) => update({ panel: id, slot: null }),
    [update],
  )
  const closePanel = useCallback(
    () => update({ panel: null, slot: null }),
    [update],
  )

  return {
    view,
    anchor,
    panel,
    slot,
    setView,
    setAnchor,
    openNew,
    openLesson,
    closePanel,
  }
}
