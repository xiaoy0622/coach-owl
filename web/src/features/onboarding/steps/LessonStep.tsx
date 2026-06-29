import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ApiError } from '@/lib/api'
import { useAuth } from '@/auth/useAuth'
import {
  Button,
  EmptyState,
  Input,
  InlineError,
  Select,
  useToast,
} from '@/components/ui'
import { schedulingApi } from '@/features/scheduling/api'
import {
  formatDate,
  formatTime,
  parseDateStr,
  todayInTz,
  zonedWallToUtc,
} from '@/features/scheduling/datetime'
import type { LessonConflictDetail } from '@/features/scheduling/types'
import { StepShell } from '../StepShell'

const DURATIONS = [30, 45, 60, 90, 120].map((m) => ({
  value: String(m),
  label: `${m} min`,
}))

function defaultDate(tz: string): string {
  const t = todayInTz(tz)
  return `${t.y}-${String(t.m).padStart(2, '0')}-${String(t.d).padStart(2, '0')}`
}

export function LessonStep({
  studentId,
  studentName,
  onScheduled,
  onSkip,
  onBack,
}: {
  studentId: string | null
  studentName: string | null
  onScheduled: () => void
  onSkip: () => void
  onBack: () => void
}) {
  const { user, org } = useAuth()
  const tz = org?.timezone ?? 'Australia/Sydney'
  const toast = useToast()

  const [date, setDate] = useState(() => defaultDate(tz))
  const [time, setTime] = useState('16:00')
  const [durationMin, setDurationMin] = useState(60)
  const [location, setLocation] = useState('')
  const [conflicts, setConflicts] = useState<LessonConflictDetail[] | null>(null)

  const mutation = useMutation({
    mutationFn: () => {
      const [hh, mm] = time.split(':').map(Number)
      const startsAt = zonedWallToUtc(parseDateStr(date), hh, mm, tz).toISOString()
      return schedulingApi.create({
        studentId: studentId!,
        coachId: user!.id,
        startsAt,
        durationMin,
        location: location.trim() || null,
      })
    },
    onSuccess: () => {
      setConflicts(null)
      toast.success('Lesson scheduled', 'Your first lesson is on the calendar.')
      onScheduled()
    },
    onError: (err) => {
      if (err instanceof ApiError && err.code === 'lesson_conflict') {
        setConflicts((err.details as LessonConflictDetail[]) ?? [])
      }
    },
  })

  const error =
    mutation.error instanceof ApiError &&
    mutation.error.code !== 'lesson_conflict'
      ? mutation.error.message
      : mutation.error && !(mutation.error instanceof ApiError)
        ? 'Could not schedule the lesson. Please try again.'
        : null

  // Step 2 was skipped — there is no student to schedule for yet.
  if (!studentId) {
    return (
      <StepShell
        title="Schedule your first lesson"
        subtitle="A lesson needs a student first."
      >
        <EmptyState
          title="No student yet"
          description="Add a student in the previous step, then come back to book their first lesson."
          action={
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Button type="button" onClick={onBack}>
                Add a student
              </Button>
              <Button type="button" variant="ghost" onClick={onSkip}>
                Skip for now
              </Button>
            </div>
          }
        />
      </StepShell>
    )
  }

  const disabled = !date || !time || mutation.isPending

  return (
    <StepShell
      title="Schedule your first lesson"
      subtitle={`Booking for ${studentName ?? 'your student'}. Times are in ${tz}.`}
    >
      <form
        className="flex flex-col gap-5"
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
      >
        <InlineError message={error} />

        <div className="rounded-2xl border border-brand-600/10 bg-brand-50/60 px-4 py-3 text-sm">
          <span className="text-muted">Student</span>{' '}
          <span className="font-display font-extrabold text-ink-deep">
            {studentName ?? 'Selected student'}
          </span>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <Input
            label="Date"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
          <Input
            label="Time"
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
          />
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <Select
            label="Duration"
            value={String(durationMin)}
            onChange={(e) => setDurationMin(Number(e.target.value))}
            options={DURATIONS}
          />
          <Input
            label="Location (optional)"
            placeholder="Studio, home, online…"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
        </div>

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

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" loading={mutation.isPending} disabled={disabled}>
            Schedule & finish
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={onSkip}
            disabled={mutation.isPending}
          >
            Skip for now
          </Button>
        </div>
      </form>
    </StepShell>
  )
}
