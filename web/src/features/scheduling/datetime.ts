// Timezone-aware date helpers for the calendar.
//
// The backend stores/serves UTC; the UI renders everything in the org timezone
// (DST-correct). Two problem classes are handled here:
//   1. UTC instant -> org-local parts (for bucketing/positioning lessons).
//   2. org-local wall time -> UTC instant (for creating/rescheduling lessons).
//
// Pure calendar-date arithmetic (week/month navigation) is done on plain
// {y,m,d} values via Date.UTC so it never drifts with the local browser tz.

export interface PlainDate {
  y: number
  m: number // 1-12
  d: number // 1-31
}

export interface ZonedParts extends PlainDate {
  hour: number
  minute: number
  weekday: number // 0=Mon .. 6=Sun
}

const pad = (n: number) => String(n).padStart(2, '0')

export function dateStr(p: PlainDate): string {
  return `${p.y}-${pad(p.m)}-${pad(p.d)}`
}

export function parseDateStr(s: string): PlainDate {
  const [y, m, d] = s.split('-').map(Number)
  return { y, m, d }
}

/** 0=Mon .. 6=Sun for a plain date. */
export function weekdayOf(p: PlainDate): number {
  const js = new Date(Date.UTC(p.y, p.m - 1, p.d)).getUTCDay() // 0=Sun
  return (js + 6) % 7
}

export function addDays(p: PlainDate, days: number): PlainDate {
  const t = new Date(Date.UTC(p.y, p.m - 1, p.d))
  t.setUTCDate(t.getUTCDate() + days)
  return { y: t.getUTCFullYear(), m: t.getUTCMonth() + 1, d: t.getUTCDate() }
}

export function addMonths(p: PlainDate, months: number): PlainDate {
  const t = new Date(Date.UTC(p.y, p.m - 1, 1))
  t.setUTCMonth(t.getUTCMonth() + months)
  return { y: t.getUTCFullYear(), m: t.getUTCMonth() + 1, d: 1 }
}

/** Monday of the week containing `p` (week starts Monday). */
export function startOfWeek(p: PlainDate): PlainDate {
  return addDays(p, -weekdayOf(p))
}

export function sameDate(a: PlainDate, b: PlainDate): boolean {
  return a.y === b.y && a.m === b.m && a.d === b.d
}

const _fmtCache = new Map<string, Intl.DateTimeFormat>()
function zonedFormatter(tz: string): Intl.DateTimeFormat {
  let f = _fmtCache.get(tz)
  if (!f) {
    f = new Intl.DateTimeFormat('en-US', {
      timeZone: tz,
      hour12: false,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
    _fmtCache.set(tz, f)
  }
  return f
}

/** Break a UTC instant into its org-local parts. */
export function zonedParts(instant: Date, tz: string): ZonedParts {
  const parts = zonedFormatter(tz).formatToParts(instant)
  const get = (t: string) => Number(parts.find((p) => p.type === t)?.value)
  let hour = get('hour')
  if (hour === 24) hour = 0 // some engines emit '24' for midnight
  const base: PlainDate = { y: get('year'), m: get('month'), d: get('day') }
  return { ...base, hour, minute: get('minute'), weekday: weekdayOf(base) }
}

/** The org-local date string for a UTC ISO string. */
export function localDateStr(iso: string, tz: string): string {
  return dateStr(zonedParts(new Date(iso), tz))
}

/** Minutes from org-local midnight for a UTC ISO string. */
export function localMinutes(iso: string, tz: string): number {
  const p = zonedParts(new Date(iso), tz)
  return p.hour * 60 + p.minute
}

/** Offset (minutes) of `tz` from UTC at `instant` (e.g. +600 for AEST). */
function tzOffsetMinutes(instant: Date, tz: string): number {
  const p = zonedParts(instant, tz)
  const asUtc = Date.UTC(p.y, p.m - 1, p.d, p.hour, p.minute, 0)
  return Math.round((asUtc - instant.getTime()) / 60000)
}

/**
 * Convert an org-local wall time (date + HH:MM) to a UTC instant, DST-correct.
 * Uses the standard two-pass offset refinement to settle near transitions.
 */
export function zonedWallToUtc(
  date: PlainDate,
  hour: number,
  minute: number,
  tz: string,
): Date {
  const wallAsUtc = Date.UTC(date.y, date.m - 1, date.d, hour, minute, 0)
  let utc = wallAsUtc - tzOffsetMinutes(new Date(wallAsUtc), tz) * 60000
  utc = wallAsUtc - tzOffsetMinutes(new Date(utc), tz) * 60000
  return new Date(utc)
}

export function todayInTz(tz: string): PlainDate {
  const p = zonedParts(new Date(), tz)
  return { y: p.y, m: p.m, d: p.d }
}

const TIME_FMT = new Map<string, Intl.DateTimeFormat>()
/** Render a UTC ISO time like `4:00 pm` in the org timezone. */
export function formatTime(iso: string, tz: string): string {
  let f = TIME_FMT.get(tz)
  if (!f) {
    f = new Intl.DateTimeFormat('en-AU', {
      timeZone: tz,
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    })
    TIME_FMT.set(tz, f)
  }
  return f.format(new Date(iso)).toLowerCase()
}

const DATE_FMT = new Map<string, Intl.DateTimeFormat>()
/** Render a UTC ISO date like `Tue 12 May 2026` in the org timezone. */
export function formatDate(iso: string, tz: string): string {
  let f = DATE_FMT.get(tz)
  if (!f) {
    f = new Intl.DateTimeFormat('en-AU', {
      timeZone: tz,
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
    DATE_FMT.set(tz, f)
  }
  return f.format(new Date(iso))
}

export const WEEKDAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
export const MONTH_LABELS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

/** End instant (UTC ms) of a lesson, for client-side overlap detection. */
export function lessonEndMs(iso: string, durationMin: number): number {
  return new Date(iso).getTime() + durationMin * 60000
}

/**
 * Flag lessons that overlap another lesson for the SAME coach (conflicts).
 * Returns a Set of conflicting lesson ids.
 */
export function findConflictIds(
  lessons: { id: string; coachId: string; startsAt: string; durationMin: number }[],
): Set<string> {
  const conflicts = new Set<string>()
  for (let i = 0; i < lessons.length; i++) {
    for (let j = i + 1; j < lessons.length; j++) {
      const a = lessons[i]
      const b = lessons[j]
      if (a.coachId !== b.coachId) continue
      const aStart = new Date(a.startsAt).getTime()
      const bStart = new Date(b.startsAt).getTime()
      const aEnd = lessonEndMs(a.startsAt, a.durationMin)
      const bEnd = lessonEndMs(b.startsAt, b.durationMin)
      if (aStart < bEnd && bStart < aEnd) {
        conflicts.add(a.id)
        conflicts.add(b.id)
      }
    }
  }
  return conflicts
}
