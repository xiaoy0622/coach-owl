import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui'
import { StepShell } from '../StepShell'

function PartyIcon() {
  return (
    <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-100 text-brand-600">
      <svg width="30" height="30" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M5 19l4.5-12 7.5 7.5L5 19Z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M14 4.5c1.5 0 2 1.5 1 2.5M17 8.5c1.5 0 2 1.5 1 2.5M19.5 5.5h.01M16.5 2.5h.01"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  )
}

export function DoneStep({ onRestart }: { onRestart: () => void }) {
  const navigate = useNavigate()
  return (
    <StepShell title="You're all set" subtitle="Your studio is ready to go.">
      <div className="flex flex-col items-start">
        <PartyIcon />
        <p className="text-[15px] text-body">
          Nice work — that's the essentials done. From here you can manage your
          roster, fill out your calendar, and start tracking payments.
        </p>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Button type="button" onClick={() => navigate('/app')}>
            Go to dashboard
          </Button>
        </div>

        <div className="mt-6 grid w-full gap-3 sm:grid-cols-2">
          <Link
            to="/app/calendar"
            className="co-focus flex items-center justify-between rounded-2xl border border-brand-600/10 bg-white px-4 py-3.5 text-ink-deep transition-colors hover:border-brand-600/30 hover:bg-brand-50"
          >
            <span className="font-display font-extrabold">Open the calendar</span>
            <span aria-hidden="true">→</span>
          </Link>
          <Link
            to="/app/students"
            className="co-focus flex items-center justify-between rounded-2xl border border-brand-600/10 bg-white px-4 py-3.5 text-ink-deep transition-colors hover:border-brand-600/30 hover:bg-brand-50"
          >
            <span className="font-display font-extrabold">View your students</span>
            <span aria-hidden="true">→</span>
          </Link>
        </div>

        <button
          type="button"
          onClick={onRestart}
          className="co-focus mt-6 rounded-lg text-sm font-semibold text-muted hover:text-ink-deep"
        >
          Start over
        </button>
      </div>
    </StepShell>
  )
}
