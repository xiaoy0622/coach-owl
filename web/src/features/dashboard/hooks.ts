// TanStack Query hooks backing the Dashboard overview.
//
// The Dashboard only READS from the existing domain APIs (scheduling, payments,
// students) — it owns no endpoints of its own. Query keys reuse the domain
// namespaces where it helps share cache (e.g. the payments overview) and add a
// `dashboard` namespace for the week-window lesson fetch.

import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { schedulingApi } from '@/features/scheduling/api'
import {
  addDays,
  dateStr,
  localDateStr,
  startOfWeek,
  todayInTz,
  zonedWallToUtc,
} from '@/features/scheduling/datetime'
import type { Lesson } from '@/features/scheduling/types'
import { paymentsApi } from '@/features/payments/api'
import { studentsApi } from '@/features/students/api'

/** UTC [from, to) bounds of the org-local week containing today. */
function currentWeekWindow(tz: string): { from: string; to: string; todayStr: string } {
  const today = todayInTz(tz)
  const weekStart = startOfWeek(today)
  const from = zonedWallToUtc(weekStart, 0, 0, tz).toISOString()
  const to = zonedWallToUtc(addDays(weekStart, 7), 0, 0, tz).toISOString()
  return { from, to, todayStr: dateStr(today) }
}

export interface WeekLessons {
  /** All lessons in the current org-local week, ascending by start. */
  week: Lesson[]
  /** Just today's lessons (org-local), ascending by start. */
  today: Lesson[]
}

/**
 * Lessons across the current week in the org timezone, split into today vs the
 * whole week. One range fetch powers both the "today" agenda and the counts.
 */
export function useDashboardLessons(tz: string | undefined) {
  const window = tz ? currentWeekWindow(tz) : null

  const query = useQuery({
    queryKey: ['dashboard', 'lessons', window?.from, window?.to],
    queryFn: ({ signal }) => schedulingApi.list(window!.from, window!.to, signal),
    enabled: Boolean(window),
  })

  const data: WeekLessons | undefined = useMemo(() => {
    if (!query.data || !window || !tz) return undefined
    const week = [...query.data.items].sort(
      (a, b) => new Date(a.startsAt).getTime() - new Date(b.startsAt).getTime(),
    )
    const today = week.filter((l) => localDateStr(l.startsAt, tz) === window.todayStr)
    return { week, today }
  }, [query.data, window, tz])

  return { ...query, data }
}

/** This month's received / outstanding (AUD). Shares cache with the payments tab. */
export function useDashboardRevenue() {
  return useQuery({
    queryKey: ['payments', 'overview'],
    queryFn: () => paymentsApi.overview(),
  })
}

export interface RosterSummary {
  activeCount: number
  /** True when the roster exceeds the page we fetched (count is a floor). */
  hasMore: boolean
  nameOf: (studentId: string) => string
}

const ROSTER_PAGE = 200

/**
 * Roster snapshot for the Dashboard: active-student count plus an id→name map
 * for the agenda. One list fetch covers both (active count derived client-side).
 */
export function useDashboardRoster() {
  const query = useQuery({
    queryKey: ['dashboard', 'roster'],
    queryFn: () => studentsApi.list({ limit: ROSTER_PAGE }),
  })

  const summary: RosterSummary | undefined = useMemo(() => {
    if (!query.data) return undefined
    const items = query.data.items
    const names = new Map(items.map((s) => [s.id, s.name]))
    return {
      activeCount: items.filter((s) => s.status === 'active').length,
      hasMore: Boolean(query.data.nextCursor),
      nameOf: (id: string) => names.get(id) ?? 'Student',
    }
  }, [query.data])

  return { ...query, data: summary }
}
