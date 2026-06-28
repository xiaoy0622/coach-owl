import { useEffect } from 'react'

/**
 * A right-hand side sheet used for the create-lesson form and lesson detail.
 * It is opened/closed via the URL (`?panel=...`) by the caller; this component
 * only renders the overlay + panel and wires Escape / backdrop to `onClose`.
 */
export function Sheet({
  title,
  subtitle,
  onClose,
  children,
  footer,
}: {
  title: string
  subtitle?: string
  onClose: () => void
  children: React.ReactNode
  footer?: React.ReactNode
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label="Close"
        onClick={onClose}
        className="absolute inset-0 bg-ink-deep/30 backdrop-blur-sm"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative flex h-full w-full max-w-md flex-col bg-cream shadow-2xl"
      >
        <header className="flex items-start justify-between gap-4 border-b border-brand-600/10 bg-white px-6 py-5">
          <div>
            <h2 className="font-display text-xl font-black text-ink-deep">
              {title}
            </h2>
            {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close panel"
            className="co-focus -mr-1 rounded-lg p-1.5 text-muted hover:bg-brand-600/[0.07] hover:text-ink-deep"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>

        {footer && (
          <footer className="border-t border-brand-600/10 bg-white px-6 py-4">
            {footer}
          </footer>
        )}
      </div>
    </div>
  )
}
