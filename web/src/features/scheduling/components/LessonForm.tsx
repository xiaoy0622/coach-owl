import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, api } from '@/lib/api'
import { useAuth } from '@/auth/useAuth'
import { Button, Input, InlineError, Select, Toggle } from '@/components/ui'
import { useToast } from '@/components/ui/useToast'
import { Sheet } from '@/features/scheduling/components/Sheet'
import { schedulingApi } from '@/features/scheduling/api'
import {
  formatDate,
  formatTime,
  parseDateStr,
  todayInTz,
  WEEKDAY_LABELS,
  zonedWallToUtc,
} from '@/features/scheduling/datetime'
import type {
  LessonConflictDetail,
  RecurrenceRuleCreate,
} from '@/features/scheduling/types'

interface StudentLite {
  id: string
  name: string
}

const DURATIONS = [30, 45, 60, 90, 120].map((m) => ({
  value: String(m),
  label: `${m} min`,
}))

function splitSlot(slot: string | null, tz: string): { date: string; time: string } {
  if (slot && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(slot)) {
    const [date, time] = slot.split('T')
    return { date, time: time.slice(0, 5) }
  }
  const t = todayInTz(tz)
  const date = `${t.y}-${String(t.m).padStart(2, '0')}-${String(t.d).padStart(2, '0')}`
  return { date, time: '16:00' }
}

export function LessonForm({
  slot,
  onClose,
}: {
  slot: string | null
  onClose: () => void
}) {
  const { user, org } = useAuth()
  const tz = org?.timezone ?? 'Australia/Sydney'
  const toast = useToast()
  const qc = useQueryClient()

  const initial = useMemo(() => splitSlot(slot, tz), [slot, tz])

  const [recurring, setRecurring] = useState(false)
  const [studentId, setStudentId] = useState('')
  const [date, setDate] = useState(initial.date)
  const [time, setTime] = useState(initial.time)
  const [durationMin, setDurationMin] = useState(60)
  const [location, setLocation] = useState('')
  const [meetingUrl, setMeetingUrl] = useState('')
  // recurrence — default to the weekday of the initial date (0=Mon..6=Sun).
  const [byweekday, setByweekday] = useState<number[]>(() => {
    const jsDay = new Date(`${initial.date}T00:00:00Z`).getUTCDay() // 0=Sun
    return [(jsDay + 6) % 7]
  })
  const [interval, setInterval] = useState(1)
  const [endDate, setEndDate] = useState('')
  const [conflicts, setConflicts] = useState<LessonConflictDetail[] | null>(null)

  // Students dropdown — gracefully falls back to a manual id input if the
  // students API isn't available yet (it's a separate Wave-2 stream).
  const studentsQuery = useQuery({
    queryKey: ['students', 'lite'],
    queryFn: ({ signal }) =>
      api.get<{ items: StudentLite[] }>('/api/v1/students?limit=200', { signal }),
    retry: false,
    staleTime: 60_000,
  })
  const students = studentsQuery.data?.items ?? []
  const manualStudent = studentsQuery.isError || students.length === 0

  const recurrenceRule: RecurrenceRuleCreate = useMemo(
    () => ({
      freq: 'weekly',
      interval,
      byweekday: [...byweekday].sort((a, b) => a - b),
      startDate: date,
      endDate: endDate || null,
      startTime: `${time}:00`,
      durationMin,
    }),
    [interval, byweekday, date, endDate, time, durationMin],
  )

  const canPreview = recurring && byweekday.length > 0 && Boolean(date)
  const previewQuery = useQuery({
    queryKey: ['recurrence-preview', recurrenceRule],
    queryFn: () => schedulingApi.previewRecurrence(recurrenceRule, 100),
    enabled: canPreview,
    retry: false,
  })

  const mutation = useMutation({
    mutationFn: () => {
      const [hh, mm] = time.split(':').map(Number)
      const startsAt = zonedWallToUtc(
        parseDateStr(date),
        hh,
        mm,
        tz,
      ).toISOString()
      return schedulingApi.create({
        studentId: studentId.trim(),
        coachId: user!.id,
        startsAt,
        durationMin,
        location: location.trim() || null,
        meetingUrl: meetingUrl.trim() || null,
        recurrence: recurring ? recurrenceRule : null,
      })
    },
    onSuccess: (page) => {
      setConflicts(null)
      qc.invalidateQueries({ queryKey: ['lessons'] })
      toast.success(
        page.items.length > 1
          ? `${page.items.length} lessons scheduled`
          : 'Lesson scheduled',
      )
      onClose()
    },
    onError: (err) => {
      if (err instanceof ApiError && err.code === 'lesson_conflict') {
        setConflicts((err.details as LessonConflictDetail[]) ?? [])
      }
    },
  })

  const toggleWeekday = (wd: number) =>
    setByweekday((prev) =>
      prev.includes(wd) ? prev.filter((d) => d !== wd) : [...prev, wd],
    )

  const error =
    mutation.error instanceof ApiError && mutation.error.code !== 'lesson_conflict'
      ? mutation.error.message
      : null

  const disabled =
    !studentId.trim() ||
    !date ||
    !time ||
    (recurring && byweekday.length === 0) ||
    mutation.isPending

  return (
    <Sheet
      title="New lesson"
      subtitle={`Times are in ${tz}`}
      onClose={onClose}
      footer={
        <div className="flex items-center justify-end gap-3">
          <Button variant="ghost" size="sm" onClick={onClose} type="button">
            Cancel
          </Button>
          <Button
            size="sm"
            type="submit"
            form="lesson-form"
            loading={mutation.isPending}
            disabled={disabled}
          >
            {recurring ? 'Create series' : 'Schedule lesson'}
          </Button>
        </div>
      }
    >
      <form
        id="lesson-form"
        className="flex flex-col gap-5"
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
      >
        <InlineError message={error} />

        {manualStudent ? (
          <Input
            label="Student ID"
            placeholder="Paste a student UUID"
            hint="The students directory isn't connected yet — paste an id for now."
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
          />
        ) : (
          <Select
            label="Student"
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
            options={[
              { value: '', label: 'Select a student…' },
              ...students.map((s) => ({ value: s.id, label: s.name })),
            ]}
          />
        )}

        <div className="rounded-2xl border border-brand-600/10 bg-white p-4">
          <Toggle
            checked={recurring}
            onChange={setRecurring}
            label="Repeats weekly"
            description="Create a recurring series instead of one lesson."
          />
        </div>

        {!recurring ? (
          <Input
            label="Date"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        ) : (
          <>
            <div>
              <span className="mb-1.5 block font-display text-sm font-extrabold text-ink-deep">
                On these days
              </span>
              <div className="flex flex-wrap gap-1.5">
                {WEEKDAY_LABELS.map((label, wd) => {
                  const active = byweekday.includes(wd)
                  return (
                    <button
                      key={label}
                      type="button"
                      onClick={() => toggleWeekday(wd)}
                      aria-pressed={active}
                      className={
                        'co-focus rounded-lg px-2.5 py-1.5 text-xs font-bold transition-colors ' +
                        (active
                          ? 'bg-brand-500 text-white'
                          : 'bg-brand-50 text-brand-700 hover:bg-brand-100')
                      }
                    >
                      {label}
                    </button>
                  )
                })}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Starts"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
              <Input
                label="Ends (optional)"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
            <Select
              label="Every"
              value={String(interval)}
              onChange={(e) => setInterval(Number(e.target.value))}
              options={[
                { value: '1', label: 'Every week' },
                { value: '2', label: 'Every 2 weeks' },
                { value: '3', label: 'Every 3 weeks' },
                { value: '4', label: 'Every 4 weeks' },
              ]}
            />
          </>
        )}

        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Time"
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
          />
          <Select
            label="Duration"
            value={String(durationMin)}
            onChange={(e) => setDurationMin(Number(e.target.value))}
            options={DURATIONS}
          />
        </div>

        <Input
          label="Location (optional)"
          placeholder="Studio, home, online…"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
        />
        <Input
          label="Meeting URL (optional)"
          placeholder="https://…"
          value={meetingUrl}
          onChange={(e) => setMeetingUrl(e.target.value)}
        />

        {canPreview && (
          <div className="rounded-2xl border border-brand-600/10 bg-brand-50/50 px-4 py-3 text-sm">
            {previewQuery.isLoading && (
              <span className="text-muted">Calculating occurrences…</span>
            )}
            {previewQuery.data && (
              <div className="text-ink-deep">
                <span className="font-bold">
                  {previewQuery.data.count} lesson
                  {previewQuery.data.count === 1 ? '' : 's'}
                </span>{' '}
                <span className="text-muted">
                  {previewQuery.data.count > 0 && (
                    <>
                      from {formatDate(previewQuery.data.occurrences[0], tz)} at{' '}
                      {formatTime(previewQuery.data.occurrences[0], tz)}
                      {previewQuery.data.count > 1 && (
                        <>
                          {' '}
                          to{' '}
                          {formatDate(
                            previewQuery.data.occurrences[
                              previewQuery.data.count - 1
                            ],
                            tz,
                          )}
                        </>
                      )}
                    </>
                  )}
                </span>
              </div>
            )}
          </div>
        )}

        {conflicts && conflicts.length > 0 && (
          <div className="rounded-2xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm font-semibold text-danger">
            <p className="mb-1">
              Conflicts with {conflicts.length} existing lesson
              {conflicts.length === 1 ? '' : 's'} for this coach:
            </p>
            <ul className="list-disc pl-5 font-medium">
              {conflicts.map((c) => (
                <li key={c.lessonId}>
                  {formatDate(c.startsAt, tz)} · {formatTime(c.startsAt, tz)} (
                  {c.durationMin} min)
                </li>
              ))}
            </ul>
          </div>
        )}
      </form>
    </Sheet>
  )
}
