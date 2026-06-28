import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/auth/useAuth'
import { PageHeader } from '@/components/PageHeader'
import {
  Button,
  Card,
  CardHeader,
  InlineError,
  Input,
  useToast,
} from '@/components/ui'
import { ApiError } from '@/lib/api'
import { PaymentsTabs } from '@/features/payments/components/PaymentsTabs'
import { StudentPicker } from '@/features/payments/components/StudentPicker'
import { invoicesApi, type InvoiceLineItem } from '@/features/payments/api'
import { paymentsKeys } from '@/features/payments/hooks'
import { formatAud } from '@/features/payments/money'

interface DraftLine {
  description: string
  quantity: string
  unitPrice: string
}

const EMPTY_LINE: DraftLine = { description: '', quantity: '1', unitPrice: '' }

export function NewInvoicePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()
  const { org } = useAuth()

  const [studentId, setStudentId] = useState('')
  const [lines, setLines] = useState<DraftLine[]>([{ ...EMPTY_LINE }])
  const [error, setError] = useState<string | null>(null)

  const gstEnabled = Boolean(org?.gstEnabled)
  const gstRate = org?.gstRate ?? 0.1

  const totals = useMemo(() => {
    const subtotal = lines.reduce(
      (sum, l) => sum + Number(l.quantity || 0) * Number(l.unitPrice || 0),
      0,
    )
    const gst = gstEnabled ? subtotal * gstRate : 0
    return { subtotal, gst, total: subtotal + gst }
  }, [lines, gstEnabled, gstRate])

  const mutation = useMutation({
    mutationFn: () => {
      const lineItems: InvoiceLineItem[] = lines.map((l) => {
        const qty = Number(l.quantity || 0)
        const unit = Number(l.unitPrice || 0)
        return {
          description: l.description,
          quantity: qty,
          unitPrice: unit.toFixed(2),
          amount: (qty * unit).toFixed(2),
        }
      })
      return invoicesApi.create({ studentId, lineItems })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: paymentsKeys.invoices })
      toast.success('Invoice generated', 'You can download the PDF from the list.')
      navigate('/app/payments/invoices')
    },
    onError: (err) =>
      setError(
        err instanceof ApiError ? err.message : 'Could not generate the invoice.',
      ),
  })

  function update(i: number, patch: Partial<DraftLine>) {
    setLines((cur) => cur.map((l, idx) => (idx === i ? { ...l, ...patch } : l)))
  }
  function addLine() {
    setLines((cur) => [...cur, { ...EMPTY_LINE }])
  }
  function removeLine(i: number) {
    setLines((cur) => (cur.length === 1 ? cur : cur.filter((_, idx) => idx !== i)))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!studentId) return setError('Choose a student first.')
    if (lines.some((l) => !l.description.trim()))
      return setError('Every line needs a description.')
    if (totals.subtotal <= 0) return setError('Add at least one priced line.')
    mutation.mutate()
  }

  return (
    <>
      <PageHeader
        title="Generate invoice"
        description="Add line items — GST and totals are calculated for you."
      />
      <PaymentsTabs />

      <Card className="max-w-3xl">
        <CardHeader
          title="Invoice details"
          subtitle={
            gstEnabled
              ? `GST (${(gstRate * 100).toFixed(0)}%) is added automatically.`
              : 'GST is off for your studio — totals are GST-free.'
          }
        />
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <InlineError message={error} />

          <StudentPicker value={studentId} onChange={setStudentId} />

          <div className="flex flex-col gap-3">
            <div className="hidden gap-3 px-1 text-xs font-extrabold uppercase tracking-wide text-muted sm:grid sm:grid-cols-[1fr_80px_120px_110px_36px]">
              <span>Description</span>
              <span>Qty</span>
              <span>Unit (AUD)</span>
              <span className="text-right">Amount</span>
              <span />
            </div>
            {lines.map((line, i) => {
              const amount = Number(line.quantity || 0) * Number(line.unitPrice || 0)
              return (
                <div
                  key={i}
                  className="grid gap-3 sm:grid-cols-[1fr_80px_120px_110px_36px] sm:items-center"
                >
                  <Input
                    value={line.description}
                    onChange={(e) => update(i, { description: e.target.value })}
                    placeholder="8 x Maths lessons"
                  />
                  <Input
                    type="number"
                    min={1}
                    value={line.quantity}
                    onChange={(e) => update(i, { quantity: e.target.value })}
                  />
                  <Input
                    type="number"
                    min={0}
                    step={0.01}
                    value={line.unitPrice}
                    onChange={(e) => update(i, { unitPrice: e.target.value })}
                    placeholder="0.00"
                  />
                  <div className="text-right font-semibold text-ink-deep">
                    {formatAud(amount)}
                  </div>
                  <button
                    type="button"
                    onClick={() => removeLine(i)}
                    aria-label="Remove line"
                    className="co-focus justify-self-end rounded-lg p-2 text-muted hover:text-danger disabled:opacity-30"
                    disabled={lines.length === 1}
                  >
                    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
                      <path
                        d="M3 3l10 10M13 3L3 13"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                    </svg>
                  </button>
                </div>
              )
            })}
            <div>
              <Button type="button" variant="ghost" size="sm" onClick={addLine}>
                + Add line
              </Button>
            </div>
          </div>

          <div className="ml-auto w-full max-w-xs rounded-2xl border border-brand-600/10 bg-brand-50/60 p-4 text-sm">
            <Row label="Subtotal" value={formatAud(totals.subtotal)} />
            {gstEnabled && (
              <Row
                label={`GST (${(gstRate * 100).toFixed(0)}%)`}
                value={formatAud(totals.gst)}
              />
            )}
            <div className="mt-2 border-t border-brand-600/15 pt-2">
              <Row label="Total (AUD)" value={formatAud(totals.total)} bold />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button type="submit" loading={mutation.isPending}>
              Generate invoice
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => navigate('/app/payments/invoices')}
            >
              Cancel
            </Button>
          </div>
        </form>
      </Card>
    </>
  )
}

function Row({
  label,
  value,
  bold,
}: {
  label: string
  value: string
  bold?: boolean
}) {
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className={bold ? 'font-display font-black text-ink-deep' : 'text-muted'}>
        {label}
      </span>
      <span className={bold ? 'font-display font-black text-ink-deep' : 'text-ink'}>
        {value}
      </span>
    </div>
  )
}
