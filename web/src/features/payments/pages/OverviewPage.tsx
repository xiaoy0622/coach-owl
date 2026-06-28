import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import {
  Button,
  Card,
  EmptyState,
  InlineError,
  Spinner,
  useToast,
} from '@/components/ui'
import { PaymentsTabs } from '@/features/payments/components/PaymentsTabs'
import { usePayments, useRevenueOverview, useStudents } from '@/features/payments/hooks'
import { formatAud, formatDateAu } from '@/features/payments/money'
import type { Payment } from '@/features/payments/api'

export function OverviewPage() {
  const overview = useRevenueOverview()
  const payments = usePayments()
  const { students } = useStudents()
  const toast = useToast()

  const nameOf = useMemo(() => {
    const map = new Map(students.map((s) => [s.id, s.name]))
    return (id: string) => map.get(id) ?? `Student ${id.slice(0, 8)}`
  }, [students])

  // Month-end view: outstanding (status=due) payments grouped by student.
  const outstanding = useMemo(() => {
    const due = (payments.data?.items ?? []).filter((p) => p.status === 'due')
    const byStudent = new Map<string, { total: number; items: Payment[] }>()
    for (const p of due) {
      const entry = byStudent.get(p.studentId) ?? { total: 0, items: [] }
      entry.total += Number(p.amount)
      entry.items.push(p)
      byStudent.set(p.studentId, entry)
    }
    return [...byStudent.entries()].sort((a, b) => b[1].total - a[1].total)
  }, [payments.data])

  return (
    <>
      <PageHeader
        title="Payments"
        description="Income at a glance, lesson packs and AUD invoices."
        action={
          <Link to="/app/payments/record">
            <Button>Record a payment</Button>
          </Link>
        }
      />
      <PaymentsTabs />

      <section aria-label="This month" className="grid gap-4 sm:grid-cols-3">
        {overview.isLoading ? (
          <Card className="sm:col-span-3 flex justify-center py-10">
            <Spinner label="Loading income…" />
          </Card>
        ) : overview.isError ? (
          <div className="sm:col-span-3">
            <InlineError message="Could not load your income overview." />
          </div>
        ) : (
          <>
            <StatCard
              label="Received this month"
              value={formatAud(overview.data?.received)}
              tone="positive"
              hint="AUD"
            />
            <StatCard
              label="Outstanding"
              value={formatAud(overview.data?.due)}
              tone="warn"
              hint="Marked as due"
            />
            <StatCard
              label="Billing period"
              value={formatDateAu(overview.data?.periodStart)}
              hint={`to ${formatDateAu(overview.data?.periodEnd)}`}
            />
          </>
        )}
      </section>

      <h2 className="mb-3 mt-9 font-display text-lg font-black text-ink-deep">
        Month-end · outstanding students
      </h2>

      {payments.isLoading ? (
        <Card className="flex justify-center py-10">
          <Spinner label="Loading…" />
        </Card>
      ) : outstanding.length === 0 ? (
        <EmptyState
          title="Nothing outstanding"
          description="When a payment is recorded as due, the student shows up here with a reminder action."
        />
      ) : (
        <Card padded={false} className="overflow-hidden">
          <ul className="divide-y divide-brand-600/10">
            {outstanding.map(([studentId, group]) => (
              <li
                key={studentId}
                className="flex flex-wrap items-center justify-between gap-3 p-4 sm:px-6"
              >
                <div>
                  <div className="font-display font-extrabold text-ink-deep">
                    {nameOf(studentId)}
                  </div>
                  <div className="text-sm text-muted">
                    {group.items.length} due ·{' '}
                    <span className="font-semibold text-danger">
                      {formatAud(group.total)}
                    </span>
                  </div>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() =>
                    // TODO(Wave 3 — notifications): wire to the reminder dispatcher.
                    toast.success(
                      'Reminder queued',
                      `A reminder for ${nameOf(studentId)} will send once notifications go live.`,
                    )
                  }
                >
                  Send reminder
                </Button>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  )
}

function StatCard({
  label,
  value,
  hint,
  tone = 'neutral',
}: {
  label: string
  value: string
  hint?: string
  tone?: 'neutral' | 'positive' | 'warn'
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
      <div
        className={`mt-2 font-display text-3xl font-black tracking-[-0.02em] ${valueTone}`}
      >
        {value}
      </div>
      {hint && <div className="mt-1 text-xs font-semibold text-muted">{hint}</div>}
    </Card>
  )
}
