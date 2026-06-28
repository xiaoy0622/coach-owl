import { Route, Routes } from 'react-router-dom'
import { OverviewPage } from '@/features/payments/pages/OverviewPage'
import { RecordPaymentPage } from '@/features/payments/pages/RecordPaymentPage'
import { PacksPage } from '@/features/payments/pages/PacksPage'
import { InvoicesPage } from '@/features/payments/pages/InvoicesPage'
import { NewInvoicePage } from '@/features/payments/pages/NewInvoicePage'

/**
 * Payments feature sub-router — mounted at /app/payments/* (see App.tsx).
 *
 * Every screen is URL-addressable (CoachOwl architecture rule):
 *   index            → income overview + month-end outstanding
 *   /record          → record a payment
 *   /packs           → lesson packs + balance (?student=<id> deep-links a student)
 *   /invoices        → invoice list + PDF download
 *   /invoices/new    → generate an invoice (GST-aware)
 */
export default function PaymentsRoutes() {
  return (
    <Routes>
      <Route index element={<OverviewPage />} />
      <Route path="record" element={<RecordPaymentPage />} />
      <Route path="packs" element={<PacksPage />} />
      <Route path="invoices" element={<InvoicesPage />} />
      <Route path="invoices/new" element={<NewInvoicePage />} />
    </Routes>
  )
}
