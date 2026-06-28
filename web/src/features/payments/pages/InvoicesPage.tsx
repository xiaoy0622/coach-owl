import { useMemo, useState } from 'react'
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
import { useInvoices, useStudents } from '@/features/payments/hooks'
import { downloadInvoicePdf, type Invoice } from '@/features/payments/api'
import { formatAud, formatDateAu } from '@/features/payments/money'

const STATUS_STYLES: Record<Invoice['status'], string> = {
  draft: 'bg-brand-100 text-brand-700',
  sent: 'bg-amber-soft text-amber-ink',
  paid: 'bg-brand-600 text-white',
}

export function InvoicesPage() {
  const { data, isLoading, isError } = useInvoices()
  const { students } = useStudents()
  const toast = useToast()
  const [downloading, setDownloading] = useState<string | null>(null)

  const nameOf = useMemo(() => {
    const map = new Map(students.map((s) => [s.id, s.name]))
    return (id: string) => map.get(id) ?? `Student ${id.slice(0, 8)}`
  }, [students])

  async function handleDownload(invoice: Invoice) {
    setDownloading(invoice.id)
    try {
      await downloadInvoicePdf(invoice)
    } catch {
      toast.error('Download failed', 'Could not fetch the invoice PDF.')
    } finally {
      setDownloading(null)
    }
  }

  const invoices = data?.items ?? []

  return (
    <>
      <PageHeader
        title="Invoices"
        description="Generate tidy AUD invoices with GST handled for you."
        action={
          <Link to="/app/payments/invoices/new">
            <Button>Generate invoice</Button>
          </Link>
        }
      />
      <PaymentsTabs />

      {isLoading ? (
        <Card className="flex justify-center py-12">
          <Spinner label="Loading invoices…" />
        </Card>
      ) : isError ? (
        <InlineError message="Could not load invoices." />
      ) : invoices.length === 0 ? (
        <EmptyState
          title="No invoices yet"
          description="Generate your first AUD invoice — GST is added automatically when it's enabled for your studio."
          action={
            <Link to="/app/payments/invoices/new">
              <Button>Generate invoice</Button>
            </Link>
          }
        />
      ) : (
        <Card padded={false} className="overflow-hidden">
          <ul className="divide-y divide-brand-600/10">
            {invoices.map((inv) => (
              <li
                key={inv.id}
                className="flex flex-wrap items-center justify-between gap-3 p-4 sm:px-6"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-display font-black text-ink-deep">
                      #{inv.number}
                    </span>
                    <span
                      className={`rounded-md px-2 py-0.5 text-xs font-extrabold ${STATUS_STYLES[inv.status]}`}
                    >
                      {inv.status}
                    </span>
                  </div>
                  <div className="text-sm text-muted">
                    {nameOf(inv.studentId)} · {formatDateAu(inv.issuedAt ?? inv.createdAt)}
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="font-display font-black text-ink-deep">
                      {formatAud(inv.total)}
                    </div>
                    {Number(inv.gstAmount) > 0 && (
                      <div className="text-xs text-muted">
                        incl. {formatAud(inv.gstAmount)} GST
                      </div>
                    )}
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    loading={downloading === inv.id}
                    onClick={() => handleDownload(inv)}
                  >
                    PDF
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  )
}
