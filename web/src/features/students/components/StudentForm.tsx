import { useState } from 'react'
import { Button, Input, InlineError, Select, Toggle } from '@/components/ui'
import type { StudentCreate, StudentStatus } from '../types'

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'paused', label: 'Paused' },
  { value: 'churned', label: 'Churned' },
]

export interface StudentFormValues {
  name: string
  email: string
  phone: string
  status: StudentStatus
  tags: string
  notes: string
  isMinor: boolean
  dateOfBirth: string
}

function toValues(initial?: Partial<StudentFormValues>): StudentFormValues {
  return {
    name: initial?.name ?? '',
    email: initial?.email ?? '',
    phone: initial?.phone ?? '',
    status: (initial?.status as StudentStatus) ?? 'active',
    tags: initial?.tags ?? '',
    notes: initial?.notes ?? '',
    isMinor: initial?.isMinor ?? false,
    dateOfBirth: initial?.dateOfBirth ?? '',
  }
}

function valuesToPayload(v: StudentFormValues): StudentCreate {
  return {
    name: v.name.trim(),
    email: v.email.trim() || null,
    phone: v.phone.trim() || null,
    status: v.status,
    tags: v.tags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean),
    notes: v.notes.trim() || null,
    isMinor: v.isMinor,
    dateOfBirth: v.dateOfBirth.trim() || null,
  }
}

export function StudentForm({
  initial,
  submitLabel,
  pending,
  error,
  onSubmit,
  onCancel,
}: {
  initial?: Partial<StudentFormValues>
  submitLabel: string
  pending?: boolean
  error?: string | null
  onSubmit: (payload: StudentCreate) => void
  onCancel?: () => void
}) {
  const [form, setForm] = useState<StudentFormValues>(() => toValues(initial))
  const [touched, setTouched] = useState(false)

  const nameError = touched && !form.name.trim() ? 'Name is required.' : undefined

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setTouched(true)
    if (!form.name.trim()) return
    onSubmit(valuesToPayload(form))
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <InlineError message={error} />

      <Input
        label="Full name"
        value={form.name}
        error={nameError}
        onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
        placeholder="Ada Lovelace"
        autoFocus
      />

      <div className="grid gap-5 sm:grid-cols-2">
        <Input
          label="Email"
          type="email"
          value={form.email}
          onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
          placeholder="ada@example.com"
        />
        <Input
          label="Phone"
          value={form.phone}
          onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
          placeholder="0400 000 000"
        />
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Select
          label="Status"
          options={STATUS_OPTIONS}
          value={form.status}
          onChange={(e) =>
            setForm((f) => ({ ...f, status: e.target.value as StudentStatus }))
          }
        />
        <Input
          label="Tags"
          value={form.tags}
          onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))}
          placeholder="vce, math"
          hint="Comma-separated."
        />
      </div>

      <div className="grid items-end gap-5 sm:grid-cols-2">
        <Input
          label="Date of birth"
          type="date"
          value={form.dateOfBirth}
          onChange={(e) =>
            setForm((f) => ({ ...f, dateOfBirth: e.target.value }))
          }
        />
        <Toggle
          id="student-is-minor"
          checked={form.isMinor}
          onChange={(checked) => setForm((f) => ({ ...f, isMinor: checked }))}
          label="Minor (under 18)"
          description="Requires at least one primary guardian."
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label
          htmlFor="student-notes"
          className="font-display text-sm font-extrabold text-ink-deep"
        >
          Notes
        </label>
        <textarea
          id="student-notes"
          value={form.notes}
          onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
          rows={4}
          placeholder="Anything worth remembering — goals, preferences, context."
          className="co-focus w-full rounded-xl border border-brand-600/15 bg-white px-3.5 py-2.5 text-[15px] text-ink hover:border-brand-600/30"
        />
      </div>

      <div className="flex items-center gap-3">
        <Button type="submit" loading={pending}>
          {submitLabel}
        </Button>
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  )
}
