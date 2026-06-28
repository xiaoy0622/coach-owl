import { cn } from '@/lib/cn'

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  tone?: 'brand' | 'dark' | 'light'
  label?: string
  className?: string
}

const sizes = {
  sm: 'h-4 w-4 border-2',
  md: 'h-6 w-6 border-2',
  lg: 'h-9 w-9 border-[3px]',
}

const tones = {
  brand: 'border-brand-600/25 border-t-brand-600',
  dark: 'border-amber-ink/30 border-t-amber-ink',
  light: 'border-white/30 border-t-white',
}

export function Spinner({ size = 'md', tone = 'brand', label, className }: SpinnerProps) {
  return (
    <span className={cn('inline-flex items-center gap-3', className)} role="status">
      <span
        className={cn('inline-block animate-spin rounded-full', sizes[size], tones[tone])}
        aria-hidden="true"
      />
      {label ? (
        <span className="text-sm font-semibold text-muted">{label}</span>
      ) : (
        <span className="sr-only">Loading</span>
      )}
    </span>
  )
}
