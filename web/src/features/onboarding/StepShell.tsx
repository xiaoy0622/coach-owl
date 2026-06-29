import type { ReactNode } from 'react'
import { Card } from '@/components/ui'

/**
 * Shared card chrome for each wizard step: a heading + supporting copy above the
 * step's body. Keeps every step visually consistent without each one
 * re-implementing the Card/title boilerplate.
 */
export function StepShell({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: ReactNode
}) {
  return (
    <Card className="max-w-2xl">
      <div className="mb-6">
        <h2 className="font-display text-2xl font-black text-ink-deep">{title}</h2>
        {subtitle && <p className="mt-1.5 text-[15px] text-body">{subtitle}</p>}
      </div>
      {children}
    </Card>
  )
}
