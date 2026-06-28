import { useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { cn } from '@/lib/cn'
import { useAuth } from '@/auth/useAuth'
import { Logo, OwlMark } from '@/components/Logo'
import { NAV_ITEMS } from '@/components/nav-items'

/**
 * Protected application shell. On desktop a fixed left sidebar; on mobile a
 * top bar (with the org name + sign-out) plus a bottom tab bar. Every nav
 * target is a real route — navigation is via <NavLink>, never in-place state.
 */
export function AppLayout() {
  const { user, org, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  const initials = (user?.name ?? '?')
    .split(' ')
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <div className="min-h-screen bg-cream">
      {/* ---------- Desktop sidebar ---------- */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-brand-600/10 bg-white/80 px-4 py-6 backdrop-blur lg:flex">
        <Link to="/app" className="co-focus mb-8 rounded-xl px-2">
          <Logo />
        </Link>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  'co-focus flex items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] font-bold transition-colors',
                  isActive
                    ? 'bg-brand-100 text-brand-700'
                    : 'text-subtle hover:bg-brand-600/[0.06] hover:text-ink-deep',
                )
              }
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <UserCard
          name={user?.name}
          orgName={org?.name}
          initials={initials}
          onSignOut={logout}
        />
      </aside>

      {/* ---------- Mobile top bar ---------- */}
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-brand-600/10 bg-cream/85 px-4 py-3 backdrop-blur lg:hidden">
        <Link to="/app" className="co-focus rounded-xl">
          <Logo size={26} />
        </Link>
        <div className="relative">
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            aria-expanded={menuOpen}
            aria-label="Account menu"
            className="co-focus flex h-9 w-9 items-center justify-center rounded-full bg-brand-600 font-display text-sm font-extrabold text-white"
          >
            {initials || <OwlMark size={18} />}
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-11 w-56 rounded-2xl border border-brand-600/10 bg-white p-3 shadow-lift">
              <div className="px-2 pb-2">
                <div className="font-display text-sm font-extrabold text-ink-deep">
                  {user?.name}
                </div>
                <div className="truncate text-xs text-muted">{org?.name}</div>
              </div>
              <button
                type="button"
                onClick={logout}
                className="co-focus w-full rounded-xl px-2 py-2 text-left text-sm font-bold text-subtle hover:bg-brand-600/[0.06] hover:text-ink-deep"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </header>

      {/* ---------- Main content ---------- */}
      <main className="px-4 pb-24 pt-6 sm:px-6 lg:ml-64 lg:px-10 lg:pb-12 lg:pt-10">
        <div className="mx-auto max-w-5xl">
          <Outlet />
        </div>
      </main>

      {/* ---------- Mobile bottom tab bar ---------- */}
      <nav className="fixed inset-x-0 bottom-0 z-40 flex border-t border-brand-600/10 bg-white/90 backdrop-blur lg:hidden">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              cn(
                'co-focus flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-bold transition-colors',
                isActive ? 'text-brand-600' : 'text-muted',
              )
            }
          >
            <span aria-hidden="true">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}

function UserCard({
  name,
  orgName,
  initials,
  onSignOut,
}: {
  name?: string
  orgName?: string
  initials: string
  onSignOut: () => void
}) {
  return (
    <div className="mt-4 rounded-2xl border border-brand-600/10 bg-brand-50/70 p-3">
      <div className="flex items-center gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-600 font-display text-sm font-extrabold text-white">
          {initials}
        </span>
        <div className="min-w-0">
          <div className="truncate font-display text-sm font-extrabold text-ink-deep">
            {name}
          </div>
          <div className="truncate text-xs text-muted">{orgName}</div>
        </div>
      </div>
      <button
        type="button"
        onClick={onSignOut}
        className="co-focus mt-2 w-full rounded-xl px-2 py-1.5 text-left text-sm font-bold text-subtle hover:bg-white hover:text-ink-deep"
      >
        Sign out
      </button>
    </div>
  )
}
