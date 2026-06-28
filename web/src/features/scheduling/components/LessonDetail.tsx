import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '@/lib/api'
import { useAuth } from '@/auth/useAuth'
import { Button, Input, InlineError, Select, Spinner } from '@/components/ui'
import { useToast } from '@/components/ui/useToast'
import { Sheet } from '@/features/scheduling/components/Sheet'
import { schedulingApi } from '@/features/scheduling/api'
import {
  formatDate,
  formatTime,
  parseDateStr,
  zonedParts,
  zonedWallToUtc,
} from '@/features/scheduling/datetime'
import { STATUS_CHIP, STATUS_LABEL } from '@/features/scheduling/status'
import type {
  Lesson,
  LessonConflictDetail,
  LessonStatus,
  LessonUpdate,
} from '@/features/scheduling/types'

const DURATIONS = [30, 45, 60, 90, 120].map((m) => ({
  value: String(m),
  label: `${m} min`,
}))

export function LessonDetail({
  lessonId,
  onClose,
}: {
  lessonId: string
  onClose: () => void
}) {
  const { org } = useAuth()
  const tz = org?.timezone ?? 'Australia/Sydney'
  const toast = useToast()
  const qc = useQueryClient()

  const query = useQuery({
    queryKey: ['lessons', 'detail', lessonId],
    queryFn: ({ signal }) => schedulingApi.get(lessonId, signal),
  })

  const lesson = query.data

  const [editing, setEditing] = useState(false)
  const [date, setDate] = useState('')
  const [time, setTime] = useState('')
  const [durationMin, setDurationMin] = useState(60)
  const [cancelReason, setCancelReason] = useState('')
  const [conflicts, setConflicts] = useState<LessonConflictDetail[] | null>(null)

  // Seed the reschedule form from the lesson once it loads.
  useEffect(() => {
    if (!lesson) return
    const p = zonedParts(new Date(lesson.startsAt), tz)
    setDate(`${p.y}-${String(p.m).padStart(2, '0')}-${String(p.d).padStart(2, '0')}`)
    setTime(`${String(p.hour).padStart(2, '0')}:${String(p.minute).padStart(2, '0')}`)
    setDurationMin(lesson.durationMin)
  }, [lesson, tz])

  const mutation = useMutation({
    mutationFn: (body: LessonUpdate) => schedulingApi.update(lessonId, body),
    onSuccess: (updated: Lesson) => {
      setConflicts(null)
      setEditing(false)
      qc.setQueryData(['lessons', 'detail', lessonId], updated)
      qc.invalidateQueries({ queryKey: ['lessons'] })
      toast.success('Lesson updated')
    },
    onError: (err) => {
      if (err instanceof ApiError && err.code === 'lesson_conflict') {
        setConflicts((err.details as LessonConflictDetail[]) ?? [])
      }
    },
  })

  const submitReschedule = () => {
    const [hh, mm] = time.split(':').map(Number)
    const startsAt = zonedWallToUtc(parseDateStr(date), hh, mm, tz).toISOString()
    mutation.mutate({ startsAt, durationMin })
  }

  const setStatus = (status: LessonStatus) => {
    const body: LessonUpdate = { status }
    if (status === 'cancelled' || status === 'no_show') {
      body.cancelReason = cancelReason.trim() || undefined
    }
    mutation.mutate(body)
  }

  const genericError =
    mutation.error instanceof ApiError &&
    mutation.error.code !== 'lesson_conflict'
      ? mutation.error.message
      : null

  const isScheduled = lesson?.status === 'scheduled'

  return (
    <Sheet
      title="Lesson"
      subtitle={lesson ? formatDate(lesson.startsAt, tz) : undefined}
      onClose={onClose}
    >
      {query.isLoading && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}
      {query.isError && (
        <InlineError
          message={
            query.error instanceof ApiError
              ? query.error.message
              : 'Could not load this lesson.'
          }
        />
      )}

      {lesson && (
        <div className="flex flex-col gap-6">
          <div className="flex items-center gap-2">
            <span
              className={
                'rounded-full border px-2.5 py-1 text-xs font-bold ' +
                STATUS_CHIP[lesson.status]
              }
            >
              {STATUS_LABEL[lesson.status]}
            </span>
            {lesson.recurrenceId && (
              <span className="rounded-full border border-brand-600/15 bg-brand-50 px-2.5 py-1 text-xs font-bold text-brand-700">
                Recurring
              </span>
            )}
            {lesson.creditDeducted && (
              <span className="rounded-full border border-emerald-600/20 bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">
                Credit used
              </span>
            )}
          </div>

          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
            <dt className="font-bold text-muted">When</dt>
            <dd className="text-ink-deep">
              {formatDate(lesson.startsAt, tz)} · {formatTime(lesson.startsAt, tz)}
            </dd>
            <dt className="font-bold text-muted">Duration</dt>
            <dd className="text-ink-deep">{lesson.durationMin} min</dd>
            {lesson.location && (
              <>
                <dt className="font-bold text-muted">Location</dt>
                <dd className="text-ink-deep">{lesson.location}</dd>
              </>
            )}
            {lesson.meetingUrl && (
              <>
                <dt className="font-bold text-muted">Meeting</dt>
                <dd className="truncate">
                  <a
                    href={lesson.meetingUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="co-focus text-brand-600 underline"
                  >
                    {lesson.meetingUrl}
                  </a>
                </dd>
              </>
            )}
            {lesson.cancelReason && (
              <>
                <dt className="font-bold text-muted">Reason</dt>
                <dd className="text-ink-deep">{lesson.cancelReason}</dd>
              </>
            )}
          </dl>

          <InlineError message={genericError} />

          {conflicts && conflicts.length > 0 && (
            <div className="rounded-2xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm font-semibold text-danger">
              Conflicts with an existing lesson:
              <ul className="mt-1 list-disc pl-5 font-medium">
                {conflicts.map((c) => (
                  <li key={c.lessonId}>
                    {formatDate(c.startsAt, tz)} · {formatTime(c.startsAt, tz)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Reschedule (scheduled only) */}
          {isScheduled && (
            <section className="rounded-2xl border border-brand-600/10 bg-white p-4">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="font-display text-sm font-black text-ink-deep">
                  Reschedule
                </h3>
                {!editing && (
                  <Button
                    variant="secondary"
                    size="sm"
                    type="button"
                    onClick={() => setEditing(true)}
                  >
                    Change time
                  </Button>
                )}
              </div>
              {editing && (
                <div className="flex flex-col gap-3">
                  <Input
                    label="Date"
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                  />
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
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      type="button"
                      onClick={() => setEditing(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      size="sm"
                      type="button"
                      loading={mutation.isPending}
                      onClick={submitReschedule}
                    >
                      Save new time
                    </Button>
                  </div>
                </div>
              )}
            </section>
          )}

          {/* Status actions */}
          {isScheduled && (
            <section className="flex flex-col gap-3">
              <h3 className="font-display text-sm font-black text-ink-deep">
                Mark as
              </h3>
              <Input
                label="Reason (for cancel / no-show)"
                placeholder="e.g. student unwell"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
              />
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  type="button"
                  onClick={() => setStatus('completed')}
                  disabled={mutation.isPending}
                >
                  Completed
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  type="button"
                  onClick={() => setStatus('no_show')}
                  disabled={mutation.isPending}
                >
                  No-show
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  type="button"
                  onClick={() => setStatus('cancelled')}
                  disabled={mutation.isPending}
                >
                  Cancel lesson
                </Button>
              </div>
            </section>
          )}

          {!isScheduled && (
            <p className="rounded-2xl bg-brand-50/60 px-4 py-3 text-sm text-muted">
              This lesson is {STATUS_LABEL[lesson.status].toLowerCase()} and can no
              longer be changed.
            </p>
          )}
        </div>
      )}
    </Sheet>
  )
}
