import { cn } from '@/lib/cn'

/**
 * Inline error banner for form-level failures (e.g. a rejected login). For
 * transient, global feedback use the Toast system instead.
 */
export function InlineError({
  message,
  className,
}: {
  message?: string | null
  className?: string
}) {
  if (!message) return null
  return (
    <div
      role="alert"
      className={cn(
        'flex items-start gap-2.5 rounded-xl border border-danger/30 bg-danger-soft px-3.5 py-3 text-sm font-semibold text-danger',
        className,
      )}
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 20 20"
        fill="none"
        className="mt-px shrink-0"
        aria-hidden="true"
      >
        <circle cx="10" cy="10" r="8.25" stroke="currentColor" strokeWidth="1.5" />
        <path
          d="M10 6v4.5"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
        <circle cx="10" cy="13.6" r="1" fill="currentColor" />
      </svg>
      <span>{message}</span>
    </div>
  )
}
