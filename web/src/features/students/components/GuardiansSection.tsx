import { useState } from 'react'
import { Button, Card, CardHeader, InlineError, Input, Spinner, Toggle, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import {
  useCreateGuardian,
  useDeleteGuardian,
  useGuardians,
  useUpdateGuardian,
} from '../hooks'
import type { Guardian } from '../types'

interface DraftGuardian {
  name: string
  relationship: string
  email: string
  phone: string
  isPrimary: boolean
}

const EMPTY: DraftGuardian = {
  name: '',
  relationship: '',
  email: '',
  phone: '',
  isPrimary: false,
}

export function GuardiansSection({
  studentId,
  isMinor,
}: {
  studentId: string
  isMinor: boolean
}) {
  const { data, isLoading, isError } = useGuardians(studentId)
  const create = useCreateGuardian(studentId)
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const toast = useToast()

  const guardians = data?.items ?? []
  const hasPrimary = guardians.some((g) => g.isPrimary)

  function add(draft: DraftGuardian) {
    setError(null)
    create.mutate(
      {
        studentId,
        name: draft.name.trim(),
        relationship: draft.relationship.trim() || null,
        email: draft.email.trim() || null,
        phone: draft.phone.trim() || null,
        isPrimary: draft.isPrimary,
      },
      {
        onSuccess: () => {
          setAdding(false)
          toast.success('Guardian added', `${draft.name} is now linked.`)
        },
        onError: (err) =>
          setError(err instanceof ApiError ? err.message : 'Could not add guardian.'),
      },
    )
  }

  return (
    <Card>
      <CardHeader
        title="Guardians"
        subtitle="Parents and carers linked to this student."
        action={
          !adding && (
            <Button size="sm" variant="secondary" onClick={() => setAdding(true)}>
              Add guardian
            </Button>
          )
        }
      />

      {isMinor && !hasPrimary && guardians.length >= 0 && (
        <div className="mb-4 rounded-xl border border-amber/30 bg-amber-soft/60 px-3.5 py-3 text-sm font-semibold text-amber-ink">
          This student is tagged “minor” — add at least one primary guardian.
        </div>
      )}

      <InlineError message={error} />

      {isLoading ? (
        <Spinner label="Loading guardians…" />
      ) : isError ? (
        <InlineError message="Could not load guardians." />
      ) : guardians.length === 0 && !adding ? (
        <p className="text-sm text-muted">No guardians linked yet.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {guardians.map((g) => (
            <GuardianRow
              key={g.id}
              guardian={g}
              studentId={studentId}
              canUnsetPrimary={!isMinor || guardians.filter((x) => x.isPrimary).length > 1}
            />
          ))}
        </ul>
      )}

      {adding && (
        <GuardianForm
          pending={create.isPending}
          onCancel={() => {
            setAdding(false)
            setError(null)
          }}
          onSubmit={add}
        />
      )}
    </Card>
  )
}

function GuardianRow({
  guardian,
  studentId,
  canUnsetPrimary,
}: {
  guardian: Guardian
  studentId: string
  canUnsetPrimary: boolean
}) {
  const update = useUpdateGuardian(studentId)
  const remove = useDeleteGuardian(studentId)
  const toast = useToast()
  const [error, setError] = useState<string | null>(null)

  function togglePrimary() {
    setError(null)
    update.mutate(
      { id: guardian.id, body: { isPrimary: !guardian.isPrimary } },
      {
        onError: (err) =>
          setError(err instanceof ApiError ? err.message : 'Could not update.'),
      },
    )
  }

  function del() {
    setError(null)
    remove.mutate(guardian.id, {
      onSuccess: () => toast.success('Guardian removed'),
      onError: (err) =>
        setError(err instanceof ApiError ? err.message : 'Could not remove.'),
    })
  }

  const contact = [guardian.email, guardian.phone].filter(Boolean).join(' · ')

  return (
    <li className="flex flex-wrap items-center gap-3 rounded-2xl border border-brand-600/10 bg-brand-50/40 px-4 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-display font-extrabold text-ink-deep">{guardian.name}</span>
          {guardian.relationship && (
            <span className="text-xs font-semibold text-muted">{guardian.relationship}</span>
          )}
          {guardian.isPrimary && (
            <span className="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-bold text-brand-700">
              Primary
            </span>
          )}
        </div>
        {contact && <div className="truncate text-sm text-muted">{contact}</div>}
        <InlineError message={error} className="mt-2" />
      </div>
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="ghost"
          loading={update.isPending}
          disabled={guardian.isPrimary && !canUnsetPrimary}
          onClick={togglePrimary}
        >
          {guardian.isPrimary ? 'Unset primary' : 'Make primary'}
        </Button>
        <Button size="sm" variant="ghost" loading={remove.isPending} onClick={del}>
          Remove
        </Button>
      </div>
    </li>
  )
}

function GuardianForm({
  pending,
  onSubmit,
  onCancel,
}: {
  pending?: boolean
  onSubmit: (draft: DraftGuardian) => void
  onCancel: () => void
}) {
  const [draft, setDraft] = useState<DraftGuardian>(EMPTY)
  const [touched, setTouched] = useState(false)

  function submit(e: React.FormEvent) {
    e.preventDefault()
    setTouched(true)
    if (!draft.name.trim()) return
    onSubmit(draft)
  }

  return (
    <form
      onSubmit={submit}
      className="mt-4 flex flex-col gap-4 rounded-2xl border border-brand-600/10 bg-white p-4"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Name"
          value={draft.name}
          error={touched && !draft.name.trim() ? 'Name is required.' : undefined}
          onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
          placeholder="Jane Smith"
          autoFocus
        />
        <Input
          label="Relationship"
          value={draft.relationship}
          onChange={(e) => setDraft((d) => ({ ...d, relationship: e.target.value }))}
          placeholder="Mother"
        />
        <Input
          label="Email"
          type="email"
          value={draft.email}
          onChange={(e) => setDraft((d) => ({ ...d, email: e.target.value }))}
        />
        <Input
          label="Phone"
          value={draft.phone}
          onChange={(e) => setDraft((d) => ({ ...d, phone: e.target.value }))}
        />
      </div>
      <Toggle
        id="guardian-primary"
        checked={draft.isPrimary}
        onChange={(checked) => setDraft((d) => ({ ...d, isPrimary: checked }))}
        label="Primary guardian"
        description="The main point of contact."
      />
      <div className="flex gap-3">
        <Button type="submit" size="sm" loading={pending}>
          Add guardian
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  )
}
