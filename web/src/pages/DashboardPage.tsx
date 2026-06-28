import { Link } from 'react-router-dom'
import { useAuth } from '@/auth/useAuth'
import { PageHeader } from '@/components/PageHeader'
import { Card } from '@/components/ui'

const STATS = [
  { label: "Today's lessons", value: '—', hint: 'Schedule a lesson to see it here' },
  { label: 'Active students', value: '—', hint: 'Add your first student' },
  { label: 'Paid this month', value: '$0', hint: 'AUD · incl. GST' },
]

const QUICK_LINKS = [
  { to: '/app/students', title: 'Add a student', body: 'Build your roster or run Smart Import.' },
  { to: '/app/calendar', title: 'Schedule a lesson', body: 'Set a one-off or recurring slot.' },
  { to: '/app/settings', title: 'Set up your studio', body: 'Timezone, currency and GST.' },
]

export function DashboardPage() {
  const { user } = useAuth()
  const firstName = user?.name?.split(' ')[0] ?? 'there'

  return (
    <>
      <PageHeader
        title={`Welcome back, ${firstName}`}
        description="Here's your studio at a glance."
      />

      <div className="grid gap-4 sm:grid-cols-3">
        {STATS.map((stat) => (
          <Card key={stat.label} className="p-5">
            <div className="text-sm font-bold text-muted">{stat.label}</div>
            <div className="mt-2 font-display text-4xl font-black tracking-[-0.02em] text-ink-deep">
              {stat.value}
            </div>
            <div className="mt-1 text-xs font-semibold text-muted">{stat.hint}</div>
          </Card>
        ))}
      </div>

      <h2 className="mb-3 mt-9 font-display text-lg font-black text-ink-deep">
        Get started
      </h2>
      <div className="grid gap-4 sm:grid-cols-3">
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
              <span className="text-brand-500 transition-transform group-hover:translate-x-0.5" aria-hidden="true">
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
