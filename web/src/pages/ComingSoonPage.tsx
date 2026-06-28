import { PageHeader } from '@/components/PageHeader'
import { EmptyState } from '@/components/ui'

/**
 * Placeholder for a Wave 2 domain. Each lives behind its own route so it's
 * deep-linkable today; the real feature swaps in behind the same path later.
 */
export function ComingSoonPage({
  title,
  description,
  blurb,
}: {
  title: string
  description: string
  blurb: string
}) {
  return (
    <>
      <PageHeader title={title} description={description} />
      <EmptyState
        icon={
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M3 7.5 12 3l9 4.5-9 4.5z" />
            <path d="M3 12l9 4.5 9-4.5M3 16.5 12 21l9-4.5" />
          </svg>
        }
        title="Coming soon"
        description={blurb}
      />
    </>
  )
}
