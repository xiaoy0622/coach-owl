import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { Card, InlineError, Spinner, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { useStudent, useUpdateStudent } from '../hooks'
import { StudentForm } from '../components/StudentForm'
import type { StudentCreate } from '../types'

export function StudentEditPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const { data: student, isLoading, isError } = useStudent(id)
  const update = useUpdateStudent(id)
  const [error, setError] = useState<string | null>(null)

  if (isLoading) {
    return (
      <div className="flex justify-center p-16">
        <Spinner label="Loading…" />
      </div>
    )
  }
  if (isError || !student) {
    return <InlineError message="Could not load this student." />
  }

  function handleSubmit(payload: StudentCreate) {
    setError(null)
    update.mutate(payload, {
      onSuccess: () => {
        toast.success('Saved', 'Student details updated.')
        navigate(`/app/students/${id}`)
      },
      onError: (err) =>
        setError(err instanceof ApiError ? err.message : 'Could not save changes.'),
    })
  }

  return (
    <>
      <PageHeader title={`Edit ${student.name}`} description="Update roster details." />
      <Card className="max-w-2xl">
        <StudentForm
          initial={{
            name: student.name,
            email: student.email ?? '',
            phone: student.phone ?? '',
            status: student.status,
            tags: student.tags.join(', '),
            notes: student.notes ?? '',
          }}
          submitLabel="Save changes"
          pending={update.isPending}
          error={error}
          onSubmit={handleSubmit}
          onCancel={() => navigate(`/app/students/${id}`)}
        />
      </Card>
    </>
  )
}
