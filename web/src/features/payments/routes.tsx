import { Route, Routes } from 'react-router-dom'
import { ComingSoonPage } from '@/pages/ComingSoonPage'

/**
 * Payments feature sub-router — mounted at /app/payments/* (see App.tsx).
 *
 * Wave 2 (Payments agent) owns this entire folder. Replace this stub with the
 * real feature: income overview (paid/outstanding this month), record a
 * payment, lesson packs/credits, and AUD invoices with GST. Use the `api`
 * client + TanStack Query; keep every screen URL-addressable.
 */
export default function PaymentsRoutes() {
  return (
    <Routes>
      <Route
        index
        element={
          <ComingSoonPage
            title="Payments"
            description="Income, lesson packs and AUD invoices with GST."
            blurb="Record payments, sell lesson packs, and generate tidy AUD invoices with GST handled — ready when tax time comes."
          />
        }
      />
    </Routes>
  )
}
