import { Input } from '@/components/ui'
import type { StructuredNote } from '../types'

/**
 * Editable view of an AI-structured note. Used wherever a coach confirms or
 * re-edits the candidate before it is saved (confirm-before-save, §1.4).
 * Topics are edited as a comma-separated list; progress/homework as free text.
 */
export function StructuredFields({
  value,
  onChange,
  disabled,
}: {
  value: StructuredNote
  onChange: (next: StructuredNote) => void
  disabled?: boolean
}) {
  return (
    <div className="flex flex-col gap-4">
      <Input
        label="Topics covered"
        value={value.topics.join(', ')}
        disabled={disabled}
        hint="Comma-separated"
        placeholder="fractions, decimals"
        onChange={(e) =>
          onChange({
            ...value,
            topics: e.target.value
              .split(',')
              .map((t) => t.trim())
              .filter(Boolean),
          })
        }
      />

      <Field
        label="Progress"
        placeholder="How did the student go? What clicked, what needs work…"
        value={value.progress ?? ''}
        disabled={disabled}
        onChange={(progress) => onChange({ ...value, progress: progress || null })}
      />

      <Field
        label="Homework"
        placeholder="What to practise before next lesson…"
        value={value.homework ?? ''}
        disabled={disabled}
        onChange={(homework) => onChange({ ...value, homework: homework || null })}
      />
    </div>
  )
}

function Field({
  label,
  value,
  placeholder,
  disabled,
  onChange,
}: {
  label: string
  value: string
  placeholder?: string
  disabled?: boolean
  onChange: (value: string) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="font-display text-sm font-extrabold text-ink-deep">
        {label}
      </label>
      <textarea
        value={value}
        disabled={disabled}
        placeholder={placeholder}
        rows={3}
        onChange={(e) => onChange(e.target.value)}
        className="co-focus w-full rounded-xl border border-brand-600/15 bg-white px-3.5 py-2.5 text-[15px] text-ink placeholder:text-muted/70 transition-colors hover:border-brand-600/30 disabled:cursor-not-allowed disabled:opacity-60"
      />
    </div>
  )
}
