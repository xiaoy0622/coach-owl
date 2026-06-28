import { cn } from '@/lib/cn'

/** The CoachOwl owl mark — copied from landing/index.html so the app and the
 *  marketing site share one identity. */
export function OwlMark({
  size = 30,
  className,
}: {
  size?: number
  className?: string
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <path d="M10 9 L13 3 L16 11 Z" fill="#0E5A4F" />
      <path d="M30 9 L27 3 L24 11 Z" fill="#0E5A4F" />
      <rect x="7" y="8" width="26" height="27" rx="13" fill="#0E5A4F" />
      <circle cx="15" cy="19" r="5.6" fill="#FBF8F1" />
      <circle cx="25" cy="19" r="5.6" fill="#FBF8F1" />
      <circle cx="15.6" cy="19.6" r="2.5" fill="#0B463D" />
      <circle cx="24.4" cy="19.6" r="2.5" fill="#0B463D" />
      <path d="M20 23 L17.4 26.2 L22.6 26.2 Z" fill="#F2A23C" />
    </svg>
  )
}

export function Logo({
  size = 30,
  className,
}: {
  size?: number
  className?: string
}) {
  return (
    <span className={cn('flex items-center gap-2.5', className)}>
      <OwlMark size={size} />
      <span className="font-display text-[21px] font-black tracking-[-0.02em] text-ink-deep">
        CoachOwl
      </span>
    </span>
  )
}
