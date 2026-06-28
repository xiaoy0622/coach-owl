import { Link } from 'react-router-dom'
import { useAuth } from '@/auth/useAuth'
import { PageHeader } from '@/components/PageHeader'
import { Card, EmptyState, InlineError, Spinner } from '@/components/ui'
import { cn } from '@/lib/cn'
import {
  useDashboardLessons,
  useDashboardRevenue,
  useDashboardRoster,
} from '@/features/dashboard/hooks'
import { formatTime } from '@/features/scheduling/datetime'
import { STATUS_CHIP, STATUS_LABEL } from '@/features/scheduling/status'
import type { Lesson } from '@/features/scheduling/types'
import { formatAud } from '@/features/payments/money'

const QUICK_LINKS = [
  { to: '/app/students/new', title: 'Add a student', body: 'Grow your roster one at a time.' },
  { to: '/app/calendar', title: 'Schedule a lesson', body: 'Set a one-off or recurring slot.' },
  { to: '/app/payments', title: 'Record a payment', body: 'Log income and check what’s due.' },
  { to: '/app/students/import', title: 'Smart Import', body: 'Paste a list — we’ll do the typing.' },
]

export function DashboardPage() {
  const { user, org } = useAuth()
  const firstName = user?.name?.split(' ')[0] ?? 'there'
  const tz = org?.timezone

  const lessons = useDashboardLessons(tz)
  const revenue = useDashboardRevenue()
  const roster = useDashboardRoster()

  return (
    <>
      <PageHeader
        title={`Welcome back, ${firstName}`}
        description="Here’s your studio at a glance."
      />

      <section aria-label="Studio summary" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Today’s lessons"
          isLoading={lessons.isLoading}
          isError={lessons.isError}
          value={lessons.data ? String(lessons.data.today.length) : undefined}
          hint={
            lessons.data
              ? `${lessons.data.week.length} this week`
              : undefined
          }
        />
        <StatCard
          label="Received this month"
          tone="positive"
          isLoading={revenue.isLoading}
          isError={revenue.isError}
          value={revenue.data ? formatAud(revenue.data.received) : undefined}
          hint="AUD"
        />
        <StatCard
          label="Outstanding"
          tone="warn"
          isLoading={revenue.isLoading}
          isError={revenue.isError}
          value={revenue.data ? formatAud(revenue.data.due) : undefined}
          hint="Marked as due"
        />
        <StatCard
          label="Active students"
          isLoading={roster.isLoading}
          isError={roster.isError}
          value={
            roster.data
              ? `${roster.data.activeCount}${roster.data.hasMore ? '+' : ''}`
              : undefined
          }
          hint="On your roster"
        />
      </section>

      <h2 className="mb-3 mt-9 font-display text-lg font-black text-ink-deep">
        Today’s schedule
      </h2>
      <TodayAgenda
        lessons={lessons}
        tz={tz}
        nameOf={roster.data?.nameOf}
      />

      <h2 className="mb-3 mt-9 font-display text-lg font-black text-ink-deep">
        Quick actions
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {QUICK_LINKS.map((link) => (
          <Link
            key={link.to}
            to={link.to}
            className="co-focus group rounded-3xl border border-brand-600/10 bg-white p-5 shadow-card transition-transform hover:-translate-y-0.5"
          >
            <div className="flex items-center justify-between">
              <span className="font-display text-[17px] font-black text-ink-deep">
                {link.title}
              </span>
              <span
                className="text-brand-500 transition-transform group-hover:translate-x-0.5"
                aria-hidden="true"
              >
                →
              </span>
            </div>
            <p className="mt-1.5 text-sm text-muted">{link.body}</p>
          </Link>
        ))}
      </div>
    </>
  )
}

function StatCard({
  label,
  value,
  hint,
  tone = 'neutral',
  isLoading,
  isError,
}: {
  label: string
  value?: string
  hint?: string
  tone?: 'neutral' | 'positive' | 'warn'
  isLoading?: boolean
  isError?: boolean
}) {
  const valueTone =
    tone === 'positive'
      ? 'text-brand-600'
      : tone === 'warn'
        ? 'text-danger'
        : 'text-ink-deep'

  return (
    <Card className="p-5">
      <div className="text-sm font-bold text-muted">{label}</div>
      {isLoading ? (
        <div className="mt-3">
          <Spinner size="sm" />
        </div>
      ) : isError ? (
        <div className="mt-2 text-sm font-semibold text-danger">Unavailable</div>
      ) : (
        <div
          className={cn(
            'mt-2 font-display text-3xl font-black tracking-[-0.02em]',
            valueTone,
          )}
        >
          {value ?? '—'}
        </div>
      )}
      {hint && !isError && (
        <div className="mt-1 text-xs font-semibold text-muted">{hint}</div>
      )}
    </Card>
  )
}

function TodayAgenda({
  lessons,
  tz,
  nameOf,
}: {
  lessons: ReturnType<typeof useDashboardLessons>
  tz: string | undefined
  nameOf?: (id: string) => string
}) {
  if (lessons.isLoading) {
    return (
      <Card className="flex justify-center py-10">
        <Spinner label="Loading today’s lessons…" />
      </Card>
    )
  }

  if (lessons.isError) {
    return <InlineError message="Could not load your schedule. Please try again." />
  }

  const today = lessons.data?.today ?? []

  if (today.length === 0) {
    return (
      <EmptyState
        title="No lessons today"
        description="Enjoy the breather, or schedule a lesson to fill the day."
        action={
          <Link
            to="/app/calendar"
            className="co-focus rounded-full bg-brand-600 px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-brand-700"
          >
            Open calendar
          </Link>
        }
      />
    )
  }

  return (
    <Card padded={false} className="overflow-hidden">
      <ul className="divide-y divide-brand-600/10">
        {today.map((lesson) => (
          <AgendaRow key={lesson.id} lesson={lesson} tz={tz} nameOf={nameOf} />
        ))}
      </ul>
    </Card>
  )
}

function AgendaRow({
  lesson,
  tz,
  nameOf,
}: {
  lesson: Lesson
  tz: string | undefined
  nameOf?: (id: string) => string
}) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 p-4 sm:px-6">
      <div className="flex items-center gap-4">
        <div className="w-20 shrink-0 font-display text-sm font-black tabular-nums text-ink-deep">
          {tz ? formatTime(lesson.startsAt, tz) : '—'}
        </div>
        <div>
          <div className="font-display font-extrabold text-ink-deep">
            {nameOf ? nameOf(lesson.studentId) : 'Student'}
          </div>
          <div className="text-sm text-muted">{lesson.durationMin} min</div>
        </div>
      </div>
      <span
        className={cn(
          'rounded-full border px-2.5 py-1 text-xs font-bold',
          STATUS_CHIP[lesson.status],
        )}
      >
        {STATUS_LABEL[lesson.status]}
      </span>
    </li>
  )
}
