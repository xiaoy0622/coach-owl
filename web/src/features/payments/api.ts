// Payments / credits / invoices API surface for the feature.
//
// Types mirror the backend Pydantic contracts (camelCase JSON; money is a
// stringified decimal — see Execution Plan §5). The PDF download bypasses the
// JSON `api` wrapper because it needs the raw blob.

import { api, getToken } from '@/lib/api'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type PaymentMethod = 'cash' | 'transfer' | 'other'
export type PaymentStatus = 'paid' | 'due'
export type InvoiceStatus = 'draft' | 'sent' | 'paid'
export type LedgerReason = 'purchase' | 'deduct' | 'refund' | 'adjust'

export interface Page<T> {
  items: T[]
  nextCursor: string | null
}

export interface Student {
  id: string
  name: string
  email?: string | null
  status?: string
}

export interface Payment {
  id: string
  orgId: string
  studentId: string
  amount: string
  method: PaymentMethod
  packId?: string | null
  paidAt: string
  note?: string | null
  status: PaymentStatus
  createdAt: string
}

export interface RevenueOverview {
  periodStart: string
  periodEnd: string
  received: string
  due: string
}

export interface CreditPack {
  id: string
  orgId: string
  studentId: string
  name: string
  totalSessions: number
  pricePerSession: string
  purchasedAt: string
  expiresAt?: string | null
  createdAt: string
}

export interface Balance {
  studentId: string
  balance: number
  threshold: number
  lowBalance: boolean
}

export interface LedgerEntry {
  id: string
  orgId: string
  studentId: string
  packId?: string | null
  lessonId?: string | null
  delta: number
  reason: LedgerReason
  createdAt: string
}

export interface InvoiceLineItem {
  description: string
  quantity: number
  unitPrice: string
  amount: string
}

export interface Invoice {
  id: string
  orgId: string
  studentId: string
  number: number
  lineItems: InvoiceLineItem[]
  subtotal: string
  gstAmount: string
  total: string
  status: InvoiceStatus
  pdfUrl?: string | null
  issuedAt?: string | null
  createdAt: string
}

// ---- Payments -------------------------------------------------------------

export interface RecordPaymentInput {
  studentId: string
  amount: string
  method: PaymentMethod
  status?: PaymentStatus
  note?: string
  packId?: string
}

export const paymentsApi = {
  list: () => api.get<Page<Payment>>('/api/v1/payments'),
  overview: () => api.get<RevenueOverview>('/api/v1/payments/overview'),
  record: (input: RecordPaymentInput) =>
    api.post<Payment>('/api/v1/payments', input),
}

// ---- Credits / packs ------------------------------------------------------

export interface BuyPackInput {
  studentId: string
  name: string
  totalSessions: number
  pricePerSession: string
  expiresAt?: string | null
}

export const creditsApi = {
  listPacks: (studentId?: string) =>
    api.get<Page<CreditPack>>(
      studentId ? `/api/v1/credits/packs?studentId=${studentId}` : '/api/v1/credits/packs',
    ),
  buyPack: (input: BuyPackInput) =>
    api.post<CreditPack>('/api/v1/credits/packs', input),
  balance: (studentId: string) =>
    api.get<Balance>(`/api/v1/credits/balance/${studentId}`),
  ledger: (studentId: string) =>
    api.get<Page<LedgerEntry>>(`/api/v1/credits/ledger?studentId=${studentId}`),
}

// ---- Invoices -------------------------------------------------------------

export interface CreateInvoiceInput {
  studentId: string
  lineItems: InvoiceLineItem[]
  status?: InvoiceStatus
}

export const invoicesApi = {
  list: () => api.get<Page<Invoice>>('/api/v1/invoices'),
  get: (id: string) => api.get<Invoice>(`/api/v1/invoices/${id}`),
  create: (input: CreateInvoiceInput) =>
    api.post<Invoice>('/api/v1/invoices', input),
}

/** Fetch the invoice PDF as a blob and trigger a browser download. */
export async function downloadInvoicePdf(invoice: Pick<Invoice, 'id' | 'number'>) {
  const token = getToken()
  const res = await fetch(`${BASE_URL}/api/v1/invoices/${invoice.id}/pdf`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error('Could not download the invoice PDF.')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `invoice-${invoice.number}.pdf`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

// ---- Students (read-only; another Wave-2 domain owns the write side) -------
//
// The picker degrades gracefully: if /students isn't implemented yet (501) the
// caller falls back to a manual student-ID input so this feature stays usable.

export const studentsApi = {
  list: () => api.get<Page<Student>>('/api/v1/students'),
}
