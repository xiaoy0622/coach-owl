import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { Button, Card, CardHeader, InlineError } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { useParseImport } from '../hooks'

const SAMPLE = `Name, Email, Phone, Guardian, Parent Phone
Tommy Smith, tommy@example.com, 0400 111 222, Jane Smith, 0400 999 888
Sarah Lee sarah@mail.com 0422 333 444 Tue/Thu 4-5pm`

export function ImportPage() {
  const navigate = useNavigate()
  const parse = useParseImport()
  const [raw, setRaw] = useState('')
  const [error, setError] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  function run() {
    setError(null)
    if (!raw.trim()) {
      setError('Paste some rows or upload a CSV first.')
      return
    }
    parse.mutate(raw, {
      onSuccess: (job) => navigate(`/app/students/import/${job.id}`),
      onError: (err) =>
        setError(err instanceof ApiError ? err.message : 'Could not parse that input.'),
    })
  }

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => setRaw(String(reader.result ?? ''))
    reader.readAsText(file)
  }

  return (
    <>
      <PageHeader
        title="Smart Import"
        description="Paste a messy list or upload a CSV — we’ll split names, contacts and guardians for you to confirm."
      />

      <Card className="max-w-3xl">
        <CardHeader
          title="Paste or upload"
          subtitle="Nothing is saved until you review and confirm."
          action={
            <Button variant="ghost" size="sm" onClick={() => setRaw(SAMPLE)}>
              Use a sample
            </Button>
          }
        />
        <InlineError message={error} />

        <textarea
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          rows={12}
          placeholder="Name, Email, Phone, Guardian…&#10;Ada Lovelace, ada@example.com, 0400 000 000"
          className="co-focus w-full rounded-xl border border-brand-600/15 bg-white px-3.5 py-2.5 font-mono text-sm text-ink hover:border-brand-600/30"
        />

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button loading={parse.isPending} onClick={run}>
            Parse rows
          </Button>
          <input
            ref={fileInput}
            type="file"
            accept=".csv,.tsv,.txt,text/csv,text/plain"
            onChange={onFile}
            className="hidden"
          />
          <Button variant="secondary" onClick={() => fileInput.current?.click()}>
            Upload CSV
          </Button>
          <span className="text-sm text-muted">
            Columns can be in any order — we detect them.
          </span>
        </div>
      </Card>
    </>
  )
}
