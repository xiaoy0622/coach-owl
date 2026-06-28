import { Link } from 'react-router-dom'
import { Card } from '@/components/ui'
import { formatDate } from '../format'
import type { LessonNote } from '../types'

/** A single structured progress note in the timeline. */
export function NoteCard({
  note,
  studentName,
  timezone,
}: {
  note: LessonNote
  studentName?: string
  timezone: string
}) {
  const { topics, progress, homework } = note.structured
  return (
    <Link to={`/app/notes/${note.id}`} className="block">
      <Card className="transition-shadow hover:shadow-lift">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <span className="font-display text-sm font-black text-ink-deep">
            {studentName ?? 'Student'}
          </span>
          <span className="text-xs font-semibold text-muted">
            {formatDate(note.createdAt, timezone)}
            {note.source === 'voice' && ' · voice'}
          </span>
        </div>

        {topics.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {topics.map((t) => (
              <span
                key={t}
                className="rounded-full bg-brand-100 px-2.5 py-0.5 text-xs font-bold text-brand-700"
              >
                {t}
              </span>
            ))}
          </div>
        )}

        {progress && (
          <p className="text-sm text-body">
            <span className="font-semibold text-ink-deep">Progress: </span>
            {progress}
          </p>
        )}
        {homework && (
          <p className="mt-1.5 text-sm text-body">
            <span className="font-semibold text-ink-deep">Homework: </span>
            {homework}
          </p>
        )}
        {!progress && !homework && topics.length === 0 && (
          <p className="text-sm text-muted">No details captured.</p>
        )}
      </Card>
    </Link>
  )
}
