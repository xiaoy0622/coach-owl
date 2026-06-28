import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import {
  Button,
  Card,
  EmptyState,
  InlineError,
  Select,
  Spinner,
} from '@/components/ui'
import { useAuth } from '@/auth/useAuth'
import { useNotes, useStudentOptions } from '../hooks'
import { NoteCard } from '../components/NoteCard'

/**
 * Lesson-notes timeline (index of /app/notes). Newest-first, filterable by
 * student via the ?student= query param (URL-addressable / refresh-safe).
 */
export function NotesTimelinePage() {
  const { org } = useAuth()
  const timezone = org?.timezone ?? 'Australia/Sydney'
  const [params, setParams] = useSearchParams()
  const studentId = params.get('student') ?? ''

  const students = useStudentOptions()
  const query = useNotes(studentId ? { studentId } : {})

  const notes = useMemo(
    () => query.data?.pages.flatMap((p) => p.items) ?? [],
    [query.data],
  )
  const nameById = useMemo(() => {
    const map = new Map<string, string>()
    for (const s of students.data?.items ?? []) map.set(s.id, s.name)
    return map
  }, [students.data])

  const studentOptions = useMemo(
    () => [
      { value: '', label: 'All students' },
      ...(students.data?.items ?? []).map((s) => ({
        value: s.id,
        label: s.name,
      })),
    ],
    [students.data],
  )

  function setStudent(value: string) {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (value) next.set('student', value)
        else next.delete('student')
        return next
      },
      { replace: true },
    )
  }

  const newNoteHref = studentId ? `/app/notes/new?student=${studentId}` : '/app/notes/new'

  return (
    <>
      <PageHeader
        title="Lesson notes"
        description="Progress notes after each lesson — tidied by AI, confirmed by you."
        action={
          <Link to={newNoteHref}>
            <Button>New note</Button>
          </Link>
        }
      />

      <Card className="mb-5 max-w-md">
        <Select
          label="Filter by student"
          options={studentOptions}
          value={studentId}
          onChange={(e) => setStudent(e.target.value)}
        />
      </Card>

      {query.isLoading ? (
        <div className="flex justify-center p-16">
          <Spinner label="Loading notes…" />
        </div>
      ) : query.isError ? (
        <InlineError message="Could not load notes. Please try again." />
      ) : notes.length === 0 ? (
        <EmptyState
          title="No notes yet"
          description="Capture a few words after a lesson and CoachOwl turns it into a clean progress note."
          action={
            <Link to={newNoteHref}>
              <Button>Capture a note</Button>
            </Link>
          }
        />
      ) : (
        <div className="flex flex-col gap-4">
          {notes.map((note) => (
            <NoteCard
              key={note.id}
              note={note}
              studentName={nameById.get(note.studentId)}
              timezone={timezone}
            />
          ))}
          {query.hasNextPage && (
            <div className="flex justify-center pt-2">
              <Button
                variant="secondary"
                loading={query.isFetchingNextPage}
                onClick={() => query.fetchNextPage()}
              >
                Load more
              </Button>
            </div>
          )}
        </div>
      )}
    </>
  )
}
