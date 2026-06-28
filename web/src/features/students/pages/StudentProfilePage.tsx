import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { Button, Card, CardHeader, InlineError, Spinner, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { useDeleteStudent, useStudent } from '../hooks'
import { StatusBadge } from '../components/StatusBadge'
import { GuardiansSection } from '../components/GuardiansSection'

export function StudentProfilePage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const { data: student, isLoading, isError } = useStudent(id)
  const remove = useDeleteStudent()
  const [confirming, setConfirming] = useState(false)

  if (isLoading) {
    return (
      <div className="flex justify-center p-16">
        <Spinner label="Loading student…" />
      </div>
    )
  }
  if (isError || !student) {
    return (
      <>
        <InlineError message="This student could not be found." />
        <div className="mt-4">
          <Link to="/app/students">
            <Button variant="secondary">Back to roster</Button>
          </Link>
        </div>
      </>
    )
  }

  const isMinor = student.tags.some((t) => t.toLowerCase() === 'minor')

  function del() {
    remove.mutate(student!.id, {
      onSuccess: () => {
        toast.success('Student removed', `${student!.name} was deleted.`)
        navigate('/app/students')
      },
      onError: (err) =>
        toast.error(
          'Could not delete',
          err instanceof ApiError ? err.message : 'Please try again.',
        ),
    })
  }

  const contact = [student.email, student.phone].filter(Boolean).join(' · ')

  return (
    <>
      <PageHeader
        title={student.name}
        description={contact || 'No contact details on file.'}
        action={
          <div className="flex gap-2">
            <Link to="edit">
              <Button variant="secondary">Edit</Button>
            </Link>
            <Link to="/app/students">
              <Button variant="ghost">Back</Button>
            </Link>
          </div>
        }
      />

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="flex flex-col gap-5 lg:col-span-2">
          <Card>
            <CardHeader title="Details" />
            <dl className="grid gap-4 sm:grid-cols-2">
              <Field label="Status">
                <StatusBadge status={student.status} />
              </Field>
              <Field label="Email">{student.email || '—'}</Field>
              <Field label="Phone">{student.phone || '—'}</Field>
              <Field label="Tags">
                {student.tags.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {student.tags.map((t) => (
                      <span
                        key={t}
                        className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-semibold text-brand-600"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                ) : (
                  '—'
                )}
              </Field>
            </dl>
          </Card>

          <Card>
            <CardHeader title="Notes" />
            {student.notes ? (
              <p className="whitespace-pre-wrap text-[15px] text-body">{student.notes}</p>
            ) : (
              <p className="text-sm text-muted">No notes yet.</p>
            )}
          </Card>
        </div>

        <div className="flex flex-col gap-5">
          <GuardiansSection studentId={student.id} isMinor={isMinor} />

          <Card>
            <CardHeader title="Danger zone" />
            {confirming ? (
              <div className="flex flex-col gap-3">
                <p className="text-sm text-body">
                  Delete {student.name}? This also removes their guardians and cannot be
                  undone.
                </p>
                <div className="flex gap-2">
                  <Button variant="danger" loading={remove.isPending} onClick={del}>
                    Delete student
                  </Button>
                  <Button variant="ghost" onClick={() => setConfirming(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <Button variant="danger" onClick={() => setConfirming(true)}>
                Delete student
              </Button>
            )}
          </Card>
        </div>
      </div>
    </>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-bold uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-1 text-[15px] text-ink-deep">{children}</dd>
    </div>
  )
}
