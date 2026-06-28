import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { Button, Card, EmptyState, InlineError, Select, Spinner } from '@/components/ui'
import { useStudents } from '../hooks'
import type { StudentStatus } from '../types'
import { StatusBadge } from '../components/StatusBadge'

const STATUS_FILTER = [
  { value: '', label: 'All statuses' },
  { value: 'active', label: 'Active' },
  { value: 'paused', label: 'Paused' },
  { value: 'churned', label: 'Churned' },
]

export function StudentListPage() {
  const [params, setParams] = useSearchParams()
  const search = params.get('q') ?? ''
  const status = (params.get('status') ?? '') as StudentStatus | ''
  const tag = params.get('tag') ?? ''

  const query = useStudents({ search, status, tag })
  const students = useMemo(
    () => query.data?.pages.flatMap((p) => p.items) ?? [],
    [query.data],
  )

  function patch(key: string, value: string) {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (value) next.set(key, value)
        else next.delete(key)
        return next
      },
      { replace: true },
    )
  }

  const hasFilters = Boolean(search || status || tag)

  return (
    <>
      <PageHeader
        title="Students"
        description="Your roster — names, contacts, status and guardians."
        action={
          <div className="flex gap-2">
            <Link to="import">
              <Button variant="secondary">Smart Import</Button>
            </Link>
            <Link to="new">
              <Button>Add student</Button>
            </Link>
          </div>
        }
      />

      <Card className="mb-5">
        <div className="grid gap-3 sm:grid-cols-[1fr_auto_1fr]">
          <input
            value={search}
            onChange={(e) => patch('q', e.target.value)}
            placeholder="Search name, email or phone…"
            aria-label="Search students"
            className="co-focus w-full rounded-xl border border-brand-600/15 bg-white px-3.5 py-2.5 text-[15px] text-ink hover:border-brand-600/30"
          />
          <Select
            options={STATUS_FILTER}
            value={status}
            aria-label="Filter by status"
            onChange={(e) => patch('status', e.target.value)}
          />
          <input
            value={tag}
            onChange={(e) => patch('tag', e.target.value)}
            placeholder="Filter by tag…"
            aria-label="Filter by tag"
            className="co-focus w-full rounded-xl border border-brand-600/15 bg-white px-3.5 py-2.5 text-[15px] text-ink hover:border-brand-600/30"
          />
        </div>
      </Card>

      {query.isLoading ? (
        <div className="flex justify-center p-16">
          <Spinner label="Loading students…" />
        </div>
      ) : query.isError ? (
        <InlineError message="Could not load students. Please try again." />
      ) : students.length === 0 ? (
        <EmptyState
          title={hasFilters ? 'No matching students' : 'No students yet'}
          description={
            hasFilters
              ? 'Try clearing your filters to see everyone.'
              : 'Add your first student, or paste a list to Smart Import.'
          }
          action={
            hasFilters ? (
              <Button variant="secondary" onClick={() => setParams({}, { replace: true })}>
                Clear filters
              </Button>
            ) : (
              <Link to="new">
                <Button>Add student</Button>
              </Link>
            )
          }
        />
      ) : (
        <Card padded={false} className="overflow-hidden">
          <ul className="divide-y divide-brand-600/10">
            {students.map((s) => (
              <li key={s.id}>
                <Link
                  to={s.id}
                  className="co-focus flex items-center gap-4 px-5 py-4 transition-colors hover:bg-brand-50/70"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-100 font-display text-sm font-black text-brand-700">
                    {initials(s.name)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-display font-extrabold text-ink-deep">
                      {s.name}
                    </div>
                    <div className="truncate text-sm text-muted">
                      {s.email || s.phone || 'No contact details'}
                    </div>
                  </div>
                  {s.tags.length > 0 && (
                    <div className="hidden gap-1.5 sm:flex">
                      {s.tags.slice(0, 3).map((t) => (
                        <span
                          key={t}
                          className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-semibold text-brand-600"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                  <StatusBadge status={s.status} />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {query.hasNextPage && (
        <div className="mt-5 flex justify-center">
          <Button
            variant="secondary"
            loading={query.isFetchingNextPage}
            onClick={() => query.fetchNextPage()}
          >
            Load more
          </Button>
        </div>
      )}
    </>
  )
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? '')
    .join('')
}
