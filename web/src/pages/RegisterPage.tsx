import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/useAuth'
import { ApiError } from '@/lib/api'
import { AuthShell } from '@/pages/AuthShell'
import { Button, Input, InlineError } from '@/components/ui'

export function RegisterPage() {
  const { register, isAuthenticated, loading } = useAuth()
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [orgName, setOrgName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (!loading && isAuthenticated) {
    return <Navigate to="/app" replace />
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await register({
        name,
        email,
        password,
        orgName: orgName.trim() || undefined,
      })
      navigate('/app', { replace: true })
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Could not create your account. Please try again.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Start free"
      subtitle="No card needed. Set up before your next lesson."
      footer={
        <>
          Already have an account?{' '}
          <Link
            to="/login"
            className="co-focus rounded font-bold text-brand-600 hover:text-brand-700"
          >
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        <InlineError message={error} />
        <Input
          label="Your name"
          autoComplete="name"
          required
          placeholder="Alex Coach"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Input
          label="Studio name"
          hint="Optional — you can change this later in Settings."
          placeholder="Brightpath Tutoring"
          value={orgName}
          onChange={(e) => setOrgName(e.target.value)}
        />
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          required
          placeholder="you@studio.com.au"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Input
          label="Password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          hint="At least 8 characters."
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" size="lg" fullWidth loading={submitting} className="mt-1">
          Create my account
        </Button>
      </form>
    </AuthShell>
  )
}
