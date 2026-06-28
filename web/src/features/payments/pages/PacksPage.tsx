import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { PageHeader } from '@/components/PageHeader'
import {
  Button,
  Card,
  CardHeader,
  EmptyState,
  InlineError,
  Input,
  Spinner,
  useToast,
} from '@/components/ui'
import { ApiError } from '@/lib/api'
import { PaymentsTabs } from '@/features/payments/components/PaymentsTabs'
import { StudentPicker } from '@/features/payments/components/StudentPicker'
import { creditsApi } from '@/features/payments/api'
import {
  paymentsKeys,
  useBalance,
  useLedger,
  usePacks,
} from '@/features/payments/hooks'
import { formatAud, formatDateAu } from '@/features/payments/money'

const REASON_LABEL: Record<string, string> = {
  purchase: 'Pack purchased',
  deduct: 'Lesson deducted',
  refund: 'Refund',
  adjust: 'Adjustment',
}

export function PacksPage() {
  // Selected student lives in the URL so the view is deep-linkable.
  const [params, setParams] = useSearchParams()
  const studentId = params.get('student') ?? ''
  const setStudentId = (id: string) => {
    setParams(id ? { student: id } : {}, { replace: true })
  }

  return (
    <>
      <PageHeader
        title="Lesson packs"
        description="Sell lesson credits and track each student's balance."
      />
      <PaymentsTabs />

      <Card className="mb-6 max-w-md">
        <StudentPicker value={studentId} onChange={setStudentId} label="Student" />
      </Card>

      {!studentId ? (
        <EmptyState
          title="Pick a student"
          description="Choose a student to see their credit balance, buy a pack, and review the ledger."
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          <div className="flex flex-col gap-6">
            <BalanceCard studentId={studentId} />
            <BuyPackCard studentId={studentId} />
          </div>
          <div className="flex flex-col gap-6">
            <PacksList studentId={studentId} />
            <LedgerList studentId={studentId} />
          </div>
        </div>
      )}
    </>
  )
}

function BalanceCard({ studentId }: { studentId: string }) {
  const { data, isLoading, isError } = useBalance(studentId)
  if (isLoading)
    return (
      <Card className="flex justify-center py-8">
        <Spinner />
      </Card>
    )
  if (isError || !data)
    return <InlineError message="Could not load the balance." />

  const low = data.lowBalance
  return (
    <Card
      className={
        low ? 'border-amber/40 bg-amber-soft/40' : undefined
      }
    >
      <div className="text-sm font-bold text-muted">Current balance</div>
      <div
        className={`mt-1 font-display text-5xl font-black tracking-[-0.02em] ${
          low ? 'text-amber-ink' : 'text-brand-600'
        }`}
      >
        {data.balance}
      </div>
      <div className="mt-1 text-sm text-muted">
        {data.balance === 1 ? 'lesson' : 'lessons'} remaining
      </div>
      {low && (
        <div className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-amber/20 px-2.5 py-1 text-xs font-extrabold text-amber-ink">
          Low balance · at or below {data.threshold}
        </div>
      )}
    </Card>
  )
}

function BuyPackCard({ studentId }: { studentId: string }) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [name, setName] = useState('10-lesson pack')
  const [totalSessions, setTotalSessions] = useState('10')
  const [pricePerSession, setPricePerSession] = useState('50.00')
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () =>
      creditsApi.buyPack({
        studentId,
        name,
        totalSessions: Number(totalSessions),
        pricePerSession: Number(pricePerSession).toFixed(2),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: paymentsKeys.packs(studentId) })
      queryClient.invalidateQueries({ queryKey: paymentsKeys.balance(studentId) })
      queryClient.invalidateQueries({ queryKey: paymentsKeys.ledger(studentId) })
      toast.success('Pack added', 'Credits were added to the student balance.')
    },
    onError: (err) =>
      setError(
        err instanceof ApiError ? err.message : 'Could not add the pack.',
      ),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (Number(totalSessions) <= 0) return setError('Sessions must be positive.')
    mutation.mutate()
  }

  return (
    <Card>
      <CardHeader title="Sell a pack" />
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <InlineError message={error} />
        <Input
          label="Pack name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Sessions"
            type="number"
            min={1}
            value={totalSessions}
            onChange={(e) => setTotalSessions(e.target.value)}
          />
          <Input
            label="Price / session"
            type="number"
            min={0}
            step={0.01}
            value={pricePerSession}
            onChange={(e) => setPricePerSession(e.target.value)}
          />
        </div>
        <Button type="submit" loading={mutation.isPending} fullWidth>
          Add pack
        </Button>
      </form>
    </Card>
  )
}

function PacksList({ studentId }: { studentId: string }) {
  const { data, isLoading } = usePacks(studentId)
  const packs = data?.items ?? []
  return (
    <Card padded={false}>
      <div className="border-b border-brand-600/10 p-4 sm:px-6">
        <h3 className="font-display text-lg font-black text-ink-deep">
          Purchase history
        </h3>
      </div>
      {isLoading ? (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      ) : packs.length === 0 ? (
        <p className="p-6 text-sm text-muted">No packs purchased yet.</p>
      ) : (
        <ul className="divide-y divide-brand-600/10">
          {packs.map((p) => (
            <li
              key={p.id}
              className="flex items-center justify-between gap-3 p-4 sm:px-6"
            >
              <div>
                <div className="font-display font-extrabold text-ink-deep">
                  {p.name}
                </div>
                <div className="text-sm text-muted">
                  {p.totalSessions} sessions · {formatDateAu(p.purchasedAt)}
                </div>
              </div>
              <div className="text-right font-semibold text-ink-deep">
                {formatAud(p.pricePerSession)}
                <span className="block text-xs font-normal text-muted">
                  per session
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

function LedgerList({ studentId }: { studentId: string }) {
  const { data, isLoading } = useLedger(studentId)
  const entries = data?.items ?? []
  return (
    <Card padded={false}>
      <div className="border-b border-brand-600/10 p-4 sm:px-6">
        <h3 className="font-display text-lg font-black text-ink-deep">
          Credit ledger
        </h3>
      </div>
      {isLoading ? (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      ) : entries.length === 0 ? (
        <p className="p-6 text-sm text-muted">No ledger activity yet.</p>
      ) : (
        <ul className="divide-y divide-brand-600/10">
          {entries.map((e) => (
            <li
              key={e.id}
              className="flex items-center justify-between gap-3 p-3.5 sm:px-6"
            >
              <div>
                <div className="text-sm font-extrabold text-ink-deep">
                  {REASON_LABEL[e.reason] ?? e.reason}
                </div>
                <div className="text-xs text-muted">
                  {formatDateAu(e.createdAt)}
                </div>
              </div>
              <div
                className={`font-display text-lg font-black ${
                  e.delta >= 0 ? 'text-brand-600' : 'text-danger'
                }`}
              >
                {e.delta >= 0 ? `+${e.delta}` : e.delta}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
