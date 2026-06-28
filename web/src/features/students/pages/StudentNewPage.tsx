import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { Card } from '@/components/ui'
import { useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { useCreateStudent } from '../hooks'
import { StudentForm } from '../components/StudentForm'
import type { StudentCreate } from '../types'

export function StudentNewPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const create = useCreateStudent()
  const [error, setError] = useState<string | null>(null)

  function handleSubmit(payload: StudentCreate) {
    setError(null)
    create.mutate(payload, {
      onSuccess: (student) => {
        toast.success('Student added', `${student.name} is on your roster.`)
        navigate(`/app/students/${student.id}`)
      },
      onError: (err) =>
        setError(
          err instanceof ApiError ? err.message : 'Could not add the student.',
        ),
    })
  }

  return (
    <>
      <PageHeader title="Add student" description="Create a new roster entry." />
      <Card className="max-w-2xl">
        <StudentForm
          submitLabel="Add student"
          pending={create.isPending}
          error={error}
          onSubmit={handleSubmit}
          onCancel={() => navigate('/app/students')}
        />
      </Card>
    </>
  )
}
