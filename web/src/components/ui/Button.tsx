import { forwardRef } from 'react'
import { cn } from '@/lib/cn'
import { Spinner } from '@/components/ui/Spinner'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  fullWidth?: boolean
}

const base =
  'co-focus inline-flex items-center justify-center gap-2 rounded-xl font-display font-extrabold ' +
  'transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-60'

const variants: Record<ButtonVariant, string> = {
  // Amber primary — the marketing site's call-to-action.
  primary:
    'bg-amber text-amber-ink shadow-amber hover:bg-amber-600 hover:-translate-y-px active:translate-y-0',
  // Outlined green secondary.
  secondary:
    'bg-white text-brand-600 border border-brand-600/20 hover:bg-brand-50 hover:border-brand-600/40',
  ghost: 'bg-transparent text-subtle hover:bg-brand-600/[0.07] hover:text-ink-deep',
  danger:
    'bg-danger text-white hover:brightness-95 active:brightness-90',
}

const sizes: Record<ButtonSize, string> = {
  sm: 'text-sm px-3.5 py-2',
  md: 'text-[15px] px-5 py-2.5',
  lg: 'text-base px-6 py-3.5',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      fullWidth = false,
      disabled,
      className,
      children,
      ...props
    },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          base,
          variants[variant],
          sizes[size],
          fullWidth && 'w-full',
          className,
        )}
        {...props}
      >
        {loading && <Spinner size="sm" tone={variant === 'primary' ? 'dark' : 'brand'} />}
        {children}
      </button>
    )
  },
)
Button.displayName = 'Button'
