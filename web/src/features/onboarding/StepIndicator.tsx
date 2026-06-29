import { cn } from '@/lib/cn'
import { STEP_ORDER, type OnboardingStepId } from './storage'

const STEP_LABELS: Record<OnboardingStepId, string> = {
  org: 'Studio',
  student: 'Student',
  lesson: 'First lesson',
  done: 'Done',
}

function Check() {
  return (
    <svg width="14" height="14" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        d="M4 10.5 8 14.5 16 5.5"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

/**
 * Horizontal step indicator: "1 Studio · 2 Student · 3 First lesson · Done".
 * Completed steps show a check, the current step is highlighted, future steps
 * are muted. Scrolls horizontally on very narrow screens.
 */
export function StepIndicator({ current }: { current: OnboardingStepId }) {
  const currentIdx = STEP_ORDER.indexOf(current)

  return (
    <ol className="mb-7 flex items-center gap-2 overflow-x-auto pb-1">
      {STEP_ORDER.map((step, idx) => {
        const isDone = idx < currentIdx
        const isCurrent = idx === currentIdx
        return (
          <li key={step} className="flex shrink-0 items-center gap-2">
            <div
              className={cn(
                'flex items-center gap-2 rounded-full px-3 py-1.5',
                isCurrent && 'bg-brand-500 text-white',
                isDone && 'bg-brand-100 text-brand-700',
                !isCurrent && !isDone && 'bg-brand-50 text-muted',
              )}
            >
              <span
                className={cn(
                  'flex h-5 w-5 items-center justify-center rounded-full text-xs font-black',
                  isCurrent && 'bg-white/25 text-white',
                  isDone && 'bg-brand-500 text-white',
                  !isCurrent && !isDone && 'bg-white text-muted',
                )}
                aria-hidden="true"
              >
                {isDone ? <Check /> : idx + 1}
              </span>
              <span className="font-display text-sm font-extrabold">
                {STEP_LABELS[step]}
              </span>
            </div>
            {idx < STEP_ORDER.length - 1 && (
              <span
                className={cn(
                  'h-px w-5 shrink-0',
                  idx < currentIdx ? 'bg-brand-300' : 'bg-brand-600/15',
                )}
                aria-hidden="true"
              />
            )}
          </li>
        )
      })}
    </ol>
  )
}
