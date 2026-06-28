import { forwardRef, useId } from 'react'
import { cn } from '@/lib/cn'

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  hint?: string
  options: Array<{ value: string; label: string }>
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, hint, options, id, className, ...props }, ref) => {
    const reactId = useId()
    const selectId = id ?? reactId
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={selectId}
            className="font-display text-sm font-extrabold text-ink-deep"
          >
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          className={cn(
            'co-focus w-full rounded-xl border border-brand-600/15 bg-white px-3.5 py-2.5 text-[15px] text-ink hover:border-brand-600/30',
            className,
          )}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {hint && <p className="text-sm text-muted">{hint}</p>}
      </div>
    )
  },
)
Select.displayName = 'Select'
