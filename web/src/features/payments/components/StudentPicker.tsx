import { Input, Select } from '@/components/ui'
import { useStudents } from '@/features/payments/hooks'

/**
 * Student selector that degrades gracefully: a dropdown when the students
 * directory is available, otherwise a manual student-ID field (so the Payments
 * feature stays usable before the Students domain ships).
 */
export function StudentPicker({
  value,
  onChange,
  label = 'Student',
}: {
  value: string
  onChange: (studentId: string) => void
  label?: string
}) {
  const { students, unavailable, isLoading } = useStudents()

  if (!unavailable && (isLoading || students.length > 0)) {
    const options = [
      { value: '', label: isLoading ? 'Loading students…' : 'Select a student' },
      ...students.map((s) => ({ value: s.id, label: s.name })),
    ]
    return (
      <Select
        label={label}
        options={options}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    )
  }

  return (
    <Input
      label={`${label} ID`}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Paste a student ID"
      hint={
        unavailable
          ? 'Student directory is not available yet — enter an ID for now.'
          : 'No students found yet — enter an ID for now.'
      }
    />
  )
}
