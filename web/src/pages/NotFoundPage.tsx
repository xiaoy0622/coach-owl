import { Link } from 'react-router-dom'
import { OwlMark } from '@/components/Logo'
import { Button } from '@/components/ui'

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-cream px-6 text-center">
      <OwlMark size={64} className="opacity-90" />
      <p className="mt-6 font-display text-sm font-extrabold uppercase tracking-[0.08em] text-amber-700">
        404
      </p>
      <h1 className="mt-2 font-display text-3xl font-black tracking-[-0.02em] text-ink-deep">
        This page flew the nest
      </h1>
      <p className="mt-2 max-w-sm text-[15px] text-body">
        The page you're after doesn't exist — or has moved somewhere calmer.
      </p>
      <div className="mt-7 flex gap-3">
        <Link to="/app">
          <Button variant="primary">Back to dashboard</Button>
        </Link>
        <Link to="/login">
          <Button variant="secondary">Sign in</Button>
        </Link>
      </div>
    </div>
  )
}
