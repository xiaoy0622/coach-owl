import { Link } from 'react-router-dom'
import { OwlMark } from '@/components/Logo'

/**
 * Two-column auth scaffold: the form on the left, a calm brand panel on the
 * right that echoes the landing page's "After · CoachOwl" feel. The panel is
 * hidden on small screens.
 */
export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
  footer: React.ReactNode
}) {
  return (
    <div className="grid min-h-screen bg-cream lg:grid-cols-[1fr_minmax(0,520px)]">
      {/* Form column */}
      <div className="flex flex-col px-6 py-8 sm:px-10">
        <Link to="/" className="co-focus inline-flex w-fit items-center gap-2.5 rounded-xl">
          <OwlMark size={30} />
          <span className="font-display text-[21px] font-black tracking-[-0.02em] text-ink-deep">
            CoachOwl
          </span>
        </Link>

        <div className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-md">
            <h1 className="font-display text-3xl font-black tracking-[-0.02em] text-ink-deep">
              {title}
            </h1>
            <p className="mt-2 text-[15px] text-body">{subtitle}</p>
            <div className="mt-7">{children}</div>
            <div className="mt-6 text-sm text-muted">{footer}</div>
          </div>
        </div>
      </div>

      {/* Brand panel */}
      <aside className="relative hidden overflow-hidden bg-gradient-to-br from-brand-600 to-brand-700 lg:block">
        <OwlMark
          size={420}
          className="pointer-events-none absolute -bottom-24 -right-16 opacity-[0.06]"
        />
        <div className="relative flex h-full flex-col justify-center px-12 text-white">
          <div className="mb-5 inline-flex w-fit items-center gap-2 rounded-full border border-amber/35 bg-amber/15 px-3.5 py-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-amber shadow-[0_0_10px_2px_rgba(242,162,60,0.8)]" />
            <span className="text-xs font-extrabold tracking-wide text-[#F6C079]">
              FOR INDEPENDENT TUTORS &amp; COACHES
            </span>
          </div>
          <h2 className="font-display text-4xl font-black leading-tight tracking-[-0.025em] text-white">
            Run your tutoring
            <br />
            business, calmly.
          </h2>
          <p className="mt-4 max-w-sm text-[15px] leading-relaxed text-[#A9D2C9]">
            Scheduling, lesson credits, payments and reminders — all in one calm
            place. Save hours every week and never miss a lesson again.
          </p>
          <ul className="mt-8 flex flex-col gap-3">
            {[
              'Every lesson in one shared calendar',
              'Credits & payments tracked automatically',
              'Reminders sent for you, every time',
            ].map((line) => (
              <li
                key={line}
                className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.07] px-4 py-3"
              >
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-500">
                  <svg width="12" height="10" viewBox="0 0 13 11" fill="none" aria-hidden="true">
                    <path
                      d="M1 5.5 L5 9.5 L12 1.5"
                      stroke="#fff"
                      strokeWidth="2.4"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
                <span className="text-sm font-bold">{line}</span>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  )
}
