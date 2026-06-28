import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useAuth } from '@/auth/useAuth'
import { authApi } from '@/auth/authApi'
import { ApiError } from '@/lib/api'
import type { Org, OrgUpdatePayload } from '@/lib/types'
import { PageHeader } from '@/components/PageHeader'
import {
  Button,
  Card,
  CardHeader,
  Input,
  InlineError,
  Select,
  Toggle,
  useToast,
} from '@/components/ui'

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

export function SettingsPage() {
  const { org, setOrg } = useAuth()
  const toast = useToast()

  // Local form state, seeded from the cached org and kept in sync if it changes.
  const [form, setForm] = useState<OrgUpdatePayload>(() => seed(org))
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setForm(seed(org))
  }, [org])

  const mutation = useMutation({
    mutationFn: (payload: OrgUpdatePayload) => authApi.updateOrg(payload),
    onSuccess: (updated: Org) => {
      setOrg(updated)
      toast.success('Settings saved', 'Your studio details are up to date.')
    },
    onError: (err) => {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Could not save your settings. Please try again.',
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
      // gstRate is entered as a percentage; store it as a fraction (0.10).
      gstRate: form.gstRate,
    })
  }

  const gstPercent = Math.round(((form.gstRate ?? 0) as number) * 1000) / 10

  return (
    <>
      <PageHeader
        title="Settings"
        description="Your studio's localisation and tax defaults."
      />

      <Card className="max-w-2xl">
        <CardHeader
          title="Studio details"
          subtitle="Used across the calendar, invoices and reminders."
        />
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
              id="gst-enabled"
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

          <div className="flex items-center gap-3">
            <Button type="submit" loading={mutation.isPending}>
              Save changes
            </Button>
          </div>
        </form>
      </Card>
    </>
  )
}

function seed(org: Org | null): OrgUpdatePayload {
  return {
    name: org?.name ?? '',
    timezone: org?.timezone ?? 'Australia/Sydney',
    currency: org?.currency ?? 'AUD',
    gstEnabled: org?.gstEnabled ?? false,
    gstRate: org?.gstRate ?? 0.1,
  }
}
