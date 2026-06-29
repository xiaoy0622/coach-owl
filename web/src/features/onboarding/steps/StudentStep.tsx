import { ApiError } from '@/lib/api'
import { Button, useToast } from '@/components/ui'
import { StudentForm } from '@/features/students/components/StudentForm'
import { useCreateStudent } from '@/features/students/hooks'
import type { Student, StudentCreate } from '@/features/students/types'
import { StepShell } from '../StepShell'

export function StudentStep({
  onCreated,
  onSkip,
}: {
  onCreated: (student: Student) => void
  onSkip: () => void
}) {
  const toast = useToast()
  const mutation = useCreateStudent()

  function handleSubmit(payload: StudentCreate) {
    mutation.mutate(payload, {
      onSuccess: (student) => {
        toast.success('Student added', `${student.name} is on your roster.`)
        onCreated(student)
      },
    })
  }

  const error =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.error
        ? 'Could not add the student. Please try again.'
        : null

  return (
    <StepShell
      title="Add your first student"
      subtitle="Just a name gets you going — email, phone and the rest are optional and editable later."
    >
      <StudentForm
        submitLabel="Add & continue"
        pending={mutation.isPending}
        error={error}
        onSubmit={handleSubmit}
      />
      <div className="mt-5 border-t border-brand-600/10 pt-5">
        <Button
          type="button"
          variant="ghost"
          onClick={onSkip}
          disabled={mutation.isPending}
        >
          Skip for now
        </Button>
      </div>
    </StepShell>
  )
}
