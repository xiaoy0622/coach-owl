import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useAuth } from '@/auth/useAuth'
import { authApi } from '@/auth/authApi'
import { ApiError } from '@/lib/api'
import type { Org, OrgUpdatePayload } from '@/lib/types'
import {
  Button,
  Input,
  InlineError,
  Select,
  Toggle,
  useToast,
} from '@/components/ui'
import { StepShell } from '../StepShell'

// Mirrors SettingsPage (web/src/pages/SettingsPage.tsx) — same option lists and
// PATCH /api/v1/org contract — so onboarding and settings stay consistent.
const TIMEZONES = [
  'Australia/Sydney',
  'Australia/Melbourne',
  'Australia/Brisbane',
  'Australia/Adelaide',
  'Australia/Perth',
  'Australia/Hobart',
  'Australia/Darwin',
  'Pacific/Auckland',
  'UTC',
].map((tz) => ({ value: tz, label: tz }))

const CURRENCIES = ['AUD', 'NZD', 'USD', 'GBP', 'EUR'].map((c) => ({
  value: c,
  label: c,
}))

function seed(org: Org | null): OrgUpdatePayload {
  return {
    name: org?.name ?? '',
    timezone: org?.timezone ?? 'Australia/Sydney',
    currency: org?.currency ?? 'AUD',
    gstEnabled: org?.gstEnabled ?? false,
    gstRate: org?.gstRate ?? 0.1,
  }
}

export function OrgStep({
  onNext,
  onSkip,
}: {
  onNext: () => void
  onSkip: () => void
}) {
  const { org, setOrg } = useAuth()
  const toast = useToast()

  const [form, setForm] = useState<OrgUpdatePayload>(() => seed(org))
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setForm(seed(org))
  }, [org])

  const mutation = useMutation({
    mutationFn: (payload: OrgUpdatePayload) => authApi.updateOrg(payload),
    onSuccess: (updated: Org) => {
      setOrg(updated)
      toast.success('Studio saved', 'Your localisation and tax defaults are set.')
      onNext()
    },
    onError: (err) => {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Could not save your studio. Please try again.',
      )
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    mutation.mutate({
      name: form.name,
      timezone: form.timezone,
      currency: form.currency,
      gstEnabled: form.gstEnabled,
      gstRate: form.gstRate,
    })
  }

  const gstPercent = Math.round(((form.gstRate ?? 0) as number) * 1000) / 10

  return (
    <StepShell
      title="Set up your studio"
      subtitle="Timezone, currency and GST power your calendar, invoices and reminders. You can change these any time in Settings."
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <InlineError message={error} />

        <Input
          label="Studio name"
          value={form.name ?? ''}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          placeholder="Brightpath Tutoring"
        />

        <div className="grid gap-5 sm:grid-cols-2">
          <Select
            label="Timezone"
            options={TIMEZONES}
            value={form.timezone ?? 'Australia/Sydney'}
            onChange={(e) => setForm((f) => ({ ...f, timezone: e.target.value }))}
            hint="Lesson times render in this zone."
          />
          <Select
            label="Currency"
            options={CURRENCIES}
            value={form.currency ?? 'AUD'}
            onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value }))}
          />
        </div>

        <div className="rounded-2xl border border-brand-600/10 bg-brand-50/60 p-4">
          <Toggle
            id="onboarding-gst-enabled"
            checked={Boolean(form.gstEnabled)}
            onChange={(checked) => setForm((f) => ({ ...f, gstEnabled: checked }))}
            label="Charge GST"
            description="Add GST to invoices for this studio."
          />
          {form.gstEnabled && (
            <div className="mt-4 max-w-[200px]">
              <Input
                label="GST rate (%)"
                type="number"
                min={0}
                max={100}
                step={0.5}
                value={gstPercent}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    gstRate: (Number(e.target.value) || 0) / 100,
                  }))
                }
              />
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" loading={mutation.isPending}>
            Save & continue
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={onSkip}
            disabled={mutation.isPending}
          >
            Skip for now
          </Button>
        </div>
      </form>
    </StepShell>
  )
}
