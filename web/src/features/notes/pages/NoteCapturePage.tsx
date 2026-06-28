import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import {
  Button,
  Card,
  CardHeader,
  InlineError,
  Select,
  Spinner,
  useToast,
} from '@/components/ui'
import { useAuth } from '@/auth/useAuth'
import { ApiError } from '@/lib/api'
import {
  useCreateNote,
  useRecentLessons,
  useStructureNote,
  useStudentOptions,
} from '../hooks'
import { StructuredFields } from '../components/StructuredFields'
import { formatLessonTime } from '../format'
import type { StructuredNote } from '../types'

/**
 * Capture flow: jot raw text → "Structure" (AI candidate) → editable
 * topics/progress/homework → Save. Nothing is persisted until the coach
 * confirms (§1.4 铁律). Voice input is a labelled TODO (out of scope for now).
 */
export function NoteCapturePage() {
  const { org } = useAuth()
  const timezone = org?.timezone ?? 'Australia/Sydney'
  const navigate = useNavigate()
  const toast = useToast()
  const [params] = useSearchParams()

  const students = useStudentOptions()
  const lessons = useRecentLessons()
  const structure = useStructureNote()
  const create = useCreateNote()

  const [studentId, setStudentId] = useState(params.get('student') ?? '')
  const [lessonId, setLessonId] = useState('')
  const [raw, setRaw] = useState('')
  const [candidate, setCandidate] = useState<StructuredNote | null>(null)
  const [error, setError] = useState<string | null>(null)

  const studentOptions = useMemo(
    () => [
      { value: '', label: 'Select a student…' },
      ...(students.data?.items ?? []).map((s) => ({ value: s.id, label: s.name })),
    ],
    [students.data],
  )

  // Lessons for the chosen student, most recent first.
  const lessonOptions = useMemo(() => {
    const all = lessons.data?.items ?? []
    const forStudent = all
      .filter((l) => l.studentId === studentId)
      .sort((a, b) => b.startsAt.localeCompare(a.startsAt))
    return [
      { value: '', label: 'Select a lesson…' },
      ...forStudent.map((l) => ({
        value: l.id,
        label: formatLessonTime(l.startsAt, timezone),
      })),
    ]
  }, [lessons.data, studentId, timezone])

  function runStructure() {
    setError(null)
    if (!raw.trim()) {
      setError('Jot a few words about the lesson first.')
      return
    }
    structure.mutate(raw, {
      onSuccess: (result) => setCandidate(result),
      onError: (err) =>
        setError(
          err instanceof ApiError ? err.message : 'Could not structure that note.',
        ),
    })
  }

  function runSave() {
    if (!candidate) return
    setError(null)
    if (!studentId) {
      setError('Choose which student this note is for.')
      return
    }
    if (!lessonId) {
      setError('Choose which lesson this note belongs to.')
      return
    }
    create.mutate(
      {
        lessonId,
        studentId,
        rawInput: raw || null,
        structured: candidate,
        source: 'text',
      },
      {
        onSuccess: () => {
          toast.success('Note saved', 'Your progress note has been added.')
          navigate(`/app/notes?student=${studentId}`)
        },
        onError: (err) =>
          setError(err instanceof ApiError ? err.message : 'Could not save the note.'),
      },
    )
  }

  return (
    <>
      <PageHeader
        title="New lesson note"
        description="Jot what happened — we’ll tidy it into topics, progress and homework for you to confirm."
        action={
          <Link to="/app/notes">
            <Button variant="ghost">Back to notes</Button>
          </Link>
        }
      />

      <div className="flex flex-col gap-5">
        <Card className="max-w-3xl">
          <CardHeader
            title="1. Capture"
            subtitle="Pick the lesson, then jot or paste your notes."
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <Select
              label="Student"
              options={studentOptions}
              value={studentId}
              onChange={(e) => {
                setStudentId(e.target.value)
                setLessonId('')
              }}
            />
            <Select
              label="Lesson"
              options={lessonOptions}
              value={lessonId}
              disabled={!studentId || lessons.isLoading}
              hint={
                studentId && lessonOptions.length === 1
                  ? 'No recent lessons for this student.'
                  : undefined
              }
              onChange={(e) => setLessonId(e.target.value)}
            />
          </div>

          <div className="mt-4 flex flex-col gap-1.5">
            <label className="font-display text-sm font-extrabold text-ink-deep">
              Your notes
            </label>
            <textarea
              value={raw}
              onChange={(e) => setRaw(e.target.value)}
              rows={6}
              placeholder="e.g. Covered fractions and decimals. Tom struggled with common denominators but improved by the end. Homework: worksheet 3."
              className="co-focus w-full rounded-xl border border-brand-600/15 bg-white px-3.5 py-2.5 text-[15px] text-ink placeholder:text-muted/70 transition-colors hover:border-brand-600/30"
            />
            <p className="text-xs text-muted">
              🎤 Voice capture is coming soon — type your notes for now.
            </p>
          </div>

          <InlineError message={error && !candidate ? error : null} />

          <div className="mt-4">
            <Button loading={structure.isPending} onClick={runStructure}>
              Structure note
            </Button>
          </div>
        </Card>

        {structure.isPending && !candidate && (
          <div className="flex justify-center p-8">
            <Spinner label="Structuring…" />
          </div>
        )}

        {candidate && (
          <Card className="max-w-3xl">
            <CardHeader
              title="2. Confirm & save"
              subtitle="Edit anything that looks off — nothing is saved until you confirm."
            />

            <StructuredFields value={candidate} onChange={setCandidate} />

            <InlineError message={error} />

            <div className="mt-5 flex flex-wrap items-center gap-3">
              <Button loading={create.isPending} onClick={runSave}>
                Save note
              </Button>
              <Button
                variant="ghost"
                onClick={() => runStructure()}
                loading={structure.isPending}
              >
                Re-structure from text
              </Button>
            </div>
          </Card>
        )}
      </div>
    </>
  )
}
