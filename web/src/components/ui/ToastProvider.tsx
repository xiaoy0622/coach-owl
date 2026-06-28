import { useCallback, useRef, useState } from 'react'
import { cn } from '@/lib/cn'
import {
  ToastContext,
  type Toast,
  type ToastContextValue,
  type ToastTone,
} from '@/components/ui/toastContext'

const TONE_STYLES: Record<ToastTone, string> = {
  success: 'border-brand-500/30 bg-white',
  error: 'border-danger/30 bg-white',
  info: 'border-brand-600/15 bg-white',
}

const TONE_DOT: Record<ToastTone, string> = {
  success: 'bg-brand-500',
  error: 'bg-danger',
  info: 'bg-amber',
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback(
    (input: Omit<Toast, 'id'>) => {
      const id = nextId.current++
      setToasts((current) => [...current, { ...input, id }])
      window.setTimeout(() => dismiss(id), 5000)
    },
    [dismiss],
  )

  const success = useCallback(
    (title: string, description?: string) => toast({ tone: 'success', title, description }),
    [toast],
  )
  const error = useCallback(
    (title: string, description?: string) => toast({ tone: 'error', title, description }),
    [toast],
  )

  const value: ToastContextValue = { toast, success, error, dismiss }

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-[100] flex flex-col items-center gap-2 p-4 sm:items-end sm:p-6">
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={cn(
              'pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-2xl border px-4 py-3 shadow-lift',
              TONE_STYLES[t.tone],
            )}
          >
            <span
              className={cn('mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full', TONE_DOT[t.tone])}
              aria-hidden="true"
            />
            <div className="min-w-0 flex-1">
              <div className="font-display text-sm font-extrabold text-ink-deep">
                {t.title}
              </div>
              {t.description && (
                <div className="mt-0.5 text-sm text-muted">{t.description}</div>
              )}
            </div>
            <button
              type="button"
              onClick={() => dismiss(t.id)}
              className="co-focus -mr-1 -mt-1 rounded-lg p-1 text-muted hover:text-ink-deep"
              aria-label="Dismiss notification"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
                <path
                  d="M2 2l10 10M12 2L2 12"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
