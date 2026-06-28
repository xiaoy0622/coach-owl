import { cn } from '@/lib/cn'
import type { StudentStatus } from '../types'

const STYLES: Record<StudentStatus, string> = {
  active: 'bg-brand-100 text-brand-700',
  paused: 'bg-amber-soft text-amber-ink',
  churned: 'bg-ink/5 text-muted',
}

const LABELS: Record<StudentStatus, string> = {
  active: 'Active',
  paused: 'Paused',
  churned: 'Churned',
}

export function StatusBadge({ status }: { status: StudentStatus }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold',
        STYLES[status],
      )}
    >
      {LABELS[status]}
    </span>
  )
}
