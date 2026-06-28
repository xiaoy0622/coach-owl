export function PageHeader({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: React.ReactNode
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-display text-3xl font-black tracking-[-0.02em] text-ink-deep">
          {title}
        </h1>
        {description && <p className="mt-1.5 text-[15px] text-body">{description}</p>}
      </div>
      {action}
    </header>
  )
}
