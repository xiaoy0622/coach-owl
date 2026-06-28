import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import {
  Button,
  Card,
  CardHeader,
  InlineError,
  Spinner,
  useToast,
} from '@/components/ui'
import { useAuth } from '@/auth/useAuth'
import { ApiError } from '@/lib/api'
import { useDeleteNote, useNote, useUpdateNote } from '../hooks'
import { StructuredFields } from '../components/StructuredFields'
import { formatDate } from '../format'
import type { StructuredNote } from '../types'

/** View + re-edit a saved note (PATCH) or delete it. URL: /app/notes/:id. */
export function NoteDetailPage() {
  const { id = '' } = useParams()
  const { org } = useAuth()
  const timezone = org?.timezone ?? 'Australia/Sydney'
  const navigate = useNavigate()
  const toast = useToast()

  const { data: note, isLoading, isError } = useNote(id)
  const update = useUpdateNote(id)
  const remove = useDeleteNote()

  const [draft, setDraft] = useState<StructuredNote | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (note) setDraft(note.structured)
  }, [note])

  if (isLoading) {
    return (
      <div className="flex justify-center p-16">
        <Spinner label="Loading note…" />
      </div>
    )
  }
  if (isError || !note || !draft) {
    return (
      <>
        <InlineError message="This note could not be found." />
        <div className="mt-4">
          <Link to="/app/notes">
            <Button variant="secondary">Back to notes</Button>
          </Link>
        </div>
      </>
    )
  }

  function save() {
    if (!draft) return
    setError(null)
    update.mutate(
      { structured: draft },
      {
        onSuccess: () => toast.success('Note updated', 'Your changes are saved.'),
        onError: (err) =>
          setError(err instanceof ApiError ? err.message : 'Could not save changes.'),
      },
    )
  }

  function del() {
    remove.mutate(id, {
      onSuccess: () => {
        toast.success('Note deleted')
        navigate('/app/notes')
      },
      onError: (err) =>
        setError(err instanceof ApiError ? err.message : 'Could not delete the note.'),
    })
  }

  return (
    <>
      <PageHeader
        title="Lesson note"
        description={`Captured ${formatDate(note.createdAt, timezone)}`}
        action={
          <Link to="/app/notes">
            <Button variant="ghost">Back to notes</Button>
          </Link>
        }
      />

      <Card className="max-w-3xl">
        <CardHeader
          title="Progress note"
          subtitle="Edit the structured summary, then save."
        />

        {note.rawInput && (
          <div className="mb-5 rounded-xl border border-brand-600/10 bg-brand-50/60 px-4 py-3">
            <p className="mb-1 text-xs font-bold uppercase tracking-wide text-muted">
              Original note
            </p>
            <p className="text-sm text-body">{note.rawInput}</p>
          </div>
        )}

        <StructuredFields value={draft} onChange={setDraft} />

        <InlineError message={error} />

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <Button loading={update.isPending} onClick={save}>
            Save changes
          </Button>
          <Button variant="danger" loading={remove.isPending} onClick={del}>
            Delete note
          </Button>
        </div>
      </Card>
    </>
  )
}
