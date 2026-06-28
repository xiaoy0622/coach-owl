import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import {
  Button,
  Card,
  InlineError,
  Input,
  Select,
  Spinner,
  useToast,
} from '@/components/ui'
import { cn } from '@/lib/cn'
import { ApiError } from '@/lib/api'
import { useCommitImport, useImportJob } from '../hooks'
import type { ImportCandidate, StudentStatus } from '../types'

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'paused', label: 'Paused' },
  { value: 'churned', label: 'Churned' },
]

export function ImportReviewPage() {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const { data: job, isLoading, isError } = useImportJob(jobId)
  const commit = useCommitImport()

  const [rows, setRows] = useState<ImportCandidate[]>([])
  const [seeded, setSeeded] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (job && !seeded) {
      setRows(job.parsed.candidates ?? [])
      setSeeded(true)
    }
  }, [job, seeded])

  if (isLoading) {
    return (
      <div className="flex justify-center p-16">
        <Spinner label="Loading candidates…" />
      </div>
    )
  }
  if (isError || !job) {
    return (
      <>
        <InlineError message="This import could not be found." />
        <div className="mt-4">
          <Link to="/app/students/import">
            <Button variant="secondary">Start over</Button>
          </Link>
        </div>
      </>
    )
  }

  const committed = job.status === 'committed'
  const active = rows.filter((r) => !r.skip)

  function update(i: number, patch: Partial<ImportCandidate>) {
    setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, ...patch } : r)))
  }

  function updateGuardian(i: number, name: string, phone: string) {
    const guardians = name.trim()
      ? [{ name: name.trim(), phone: phone.trim() || null, isPrimary: true }]
      : []
    update(i, { guardians })
  }

  function runCommit() {
    if (!job) return
    setError(null)
    const toCreate = active.filter((r) => r.name.trim())
    if (toCreate.length === 0) {
      setError('Add a name to at least one row before importing.')
      return
    }
    commit.mutate(
      { jobId, parsed: { ...job.parsed, candidates: rows } },
      {
        onSuccess: (res) => {
          const n = res.parsed.createdStudentIds?.length ?? toCreate.length
          toast.success('Import complete', `${n} student${n === 1 ? '' : 's'} added.`)
          navigate('/app/students')
        },
        onError: (err) =>
          setError(err instanceof ApiError ? err.message : 'Could not import.'),
      },
    )
  }

  return (
    <>
      <PageHeader
        title="Review import"
        description="Correct anything that looks off, drop rows you don’t want, then import."
        action={
          <Link to="/app/students/import">
            <Button variant="ghost">Start over</Button>
          </Link>
        }
      />

      {committed && (
        <div className="mb-5 rounded-xl border border-brand-500/30 bg-brand-50 px-4 py-3 text-sm font-semibold text-brand-700">
          This import was already committed.
        </div>
      )}

      <InlineError message={error} />

      <div className="mb-4 text-sm text-muted">
        {active.length} of {rows.length} row{rows.length === 1 ? '' : 's'} selected · source:{' '}
        {job.parsed.source}
      </div>

      <div className="flex flex-col gap-4">
        {rows.map((row, i) => (
          <Card
            key={i}
            padded={false}
            className={cn('p-4', row.skip && 'opacity-50')}
          >
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="font-display text-sm font-black text-ink-deep">
                  Row {i + 1}
                </span>
                <ConfidenceBadge value={row.confidence} />
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => update(i, { skip: !row.skip })}
              >
                {row.skip ? 'Include' : 'Remove'}
              </Button>
            </div>

            {row.warnings?.length > 0 && (
              <ul className="mb-3 list-inside list-disc text-xs font-semibold text-amber-ink">
                {row.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            )}

            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="Name"
                value={row.name}
                disabled={row.skip || committed}
                onChange={(e) => update(i, { name: e.target.value })}
              />
              <Select
                label="Status"
                options={STATUS_OPTIONS}
                value={row.status}
                disabled={row.skip || committed}
                onChange={(e) => update(i, { status: e.target.value as StudentStatus })}
              />
              <Input
                label="Email"
                value={row.email ?? ''}
                disabled={row.skip || committed}
                onChange={(e) => update(i, { email: e.target.value || null })}
              />
              <Input
                label="Phone"
                value={row.phone ?? ''}
                disabled={row.skip || committed}
                onChange={(e) => update(i, { phone: e.target.value || null })}
              />
              <Input
                label="Tags"
                value={row.tags.join(', ')}
                disabled={row.skip || committed}
                onChange={(e) =>
                  update(i, {
                    tags: e.target.value.split(',').map((t) => t.trim()).filter(Boolean),
                  })
                }
                hint="Comma-separated"
              />
              {row.scheduleText && (
                <Input
                  label="Detected schedule (informational)"
                  value={row.scheduleText}
                  disabled
                  hint="Set this up later in the calendar."
                />
              )}
              <Input
                label="Guardian name"
                value={row.guardians[0]?.name ?? ''}
                disabled={row.skip || committed}
                onChange={(e) =>
                  updateGuardian(i, e.target.value, row.guardians[0]?.phone ?? '')
                }
              />
              <Input
                label="Guardian phone"
                value={row.guardians[0]?.phone ?? ''}
                disabled={row.skip || committed || !row.guardians[0]?.name}
                onChange={(e) =>
                  updateGuardian(i, row.guardians[0]?.name ?? '', e.target.value)
                }
              />
            </div>
          </Card>
        ))}
      </div>

      <div className="mt-6 flex items-center gap-3">
        <Button
          loading={commit.isPending}
          disabled={committed || active.length === 0}
          onClick={runCommit}
        >
          Import {active.length} student{active.length === 1 ? '' : 's'}
        </Button>
        <Link to="/app/students">
          <Button variant="ghost">Cancel</Button>
        </Link>
      </div>
    </>
  )
}

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round((value ?? 0) * 100)
  const tone =
    pct >= 80
      ? 'bg-brand-100 text-brand-700'
      : pct >= 50
        ? 'bg-amber-soft text-amber-ink'
        : 'bg-danger-soft text-danger'
  return (
    <span className={cn('rounded-full px-2 py-0.5 text-xs font-bold', tone)}>
      {pct}% match
    </span>
  )
}
