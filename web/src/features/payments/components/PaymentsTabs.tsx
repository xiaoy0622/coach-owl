import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/cn'

const TABS = [
  { to: '/app/payments', label: 'Overview', end: true },
  { to: '/app/payments/record', label: 'Record payment', end: false },
  { to: '/app/payments/packs', label: 'Lesson packs', end: false },
  { to: '/app/payments/invoices', label: 'Invoices', end: false },
]

/** Sub-navigation across the Payments feature; each tab is its own route. */
export function PaymentsTabs() {
  return (
    <nav className="mb-6 flex flex-wrap gap-1.5 rounded-2xl border border-brand-600/10 bg-white p-1.5 shadow-card">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.end}
          className={({ isActive }) =>
            cn(
              'co-focus rounded-xl px-4 py-2 font-display text-sm font-extrabold transition-colors',
              isActive
                ? 'bg-brand-600 text-white'
                : 'text-subtle hover:bg-brand-600/[0.07] hover:text-ink-deep',
            )
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  )
}
