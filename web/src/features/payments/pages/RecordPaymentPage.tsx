import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { PageHeader } from '@/components/PageHeader'
import {
  Button,
  Card,
  CardHeader,
  InlineError,
  Input,
  Select,
  useToast,
} from '@/components/ui'
import { ApiError } from '@/lib/api'
import { PaymentsTabs } from '@/features/payments/components/PaymentsTabs'
import { StudentPicker } from '@/features/payments/components/StudentPicker'
import { paymentsApi, type PaymentMethod, type PaymentStatus } from '@/features/payments/api'
import { paymentsKeys } from '@/features/payments/hooks'

const METHODS: Array<{ value: PaymentMethod; label: string }> = [
  { value: 'cash', label: 'Cash' },
  { value: 'transfer', label: 'Bank transfer' },
  { value: 'other', label: 'Other' },
]

const STATUSES: Array<{ value: PaymentStatus; label: string }> = [
  { value: 'paid', label: 'Paid' },
  { value: 'due', label: 'Due (outstanding)' },
]

export function RecordPaymentPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()

  const [studentId, setStudentId] = useState('')
  const [amount, setAmount] = useState('')
  const [method, setMethod] = useState<PaymentMethod>('cash')
  const [status, setStatus] = useState<PaymentStatus>('paid')
  const [note, setNote] = useState('')
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () =>
      paymentsApi.record({
        studentId,
        amount: Number(amount).toFixed(2),
        method,
        status,
        note: note || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: paymentsKeys.payments })
      queryClient.invalidateQueries({ queryKey: paymentsKeys.overview })
      toast.success('Payment recorded', 'Your income overview is up to date.')
      navigate('/app/payments')
    },
    onError: (err) => {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Could not record the payment. Please try again.',
      )
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!studentId) return setError('Choose a student first.')
    if (!amount || Number(amount) <= 0)
      return setError('Enter an amount greater than zero.')
    mutation.mutate()
  }

  return (
    <>
      <PageHeader
        title="Record a payment"
        description="Log cash, transfers or other payments against a student."
      />
      <PaymentsTabs />

      <Card className="max-w-2xl">
        <CardHeader
          title="Payment details"
          subtitle="Recorded in AUD and reflected in this month's income."
        />
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <InlineError message={error} />

          <StudentPicker value={studentId} onChange={setStudentId} />

          <div className="grid gap-5 sm:grid-cols-2">
            <Input
              label="Amount (AUD)"
              type="number"
              min={0}
              step={0.01}
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="120.00"
            />
            <Select
              label="Method"
              options={METHODS}
              value={method}
              onChange={(e) => setMethod(e.target.value as PaymentMethod)}
            />
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <Select
              label="Status"
              options={STATUSES}
              value={status}
              onChange={(e) => setStatus(e.target.value as PaymentStatus)}
              hint="Mark as due to chase it at month-end."
            />
            <Input
              label="Note (optional)"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Term 1 lessons"
            />
          </div>

          <div className="flex items-center gap-3">
            <Button type="submit" loading={mutation.isPending}>
              Record payment
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => navigate('/app/payments')}
            >
              Cancel
            </Button>
          </div>
        </form>
      </Card>
    </>
  )
}
