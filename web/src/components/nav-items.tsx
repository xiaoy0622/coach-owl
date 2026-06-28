import type { ReactNode } from 'react'

export interface NavItem {
  to: string
  label: string
  /** Match this route exactly (used for the index dashboard route). */
  end?: boolean
  icon: ReactNode
}

const iconProps = {
  width: 22,
  height: 22,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

// Nav items map 1:1 to the protected routes under /app. Each future domain
// (Wave 2) gets its own entry here and a matching <Route>.
export const NAV_ITEMS: NavItem[] = [
  {
    to: '/app',
    label: 'Dashboard',
    end: true,
    icon: (
      <svg {...iconProps}>
        <rect x="3" y="3" width="7.5" height="7.5" rx="1.5" />
        <rect x="13.5" y="3" width="7.5" height="7.5" rx="1.5" />
        <rect x="3" y="13.5" width="7.5" height="7.5" rx="1.5" />
        <rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.5" />
      </svg>
    ),
  },
  {
    to: '/app/students',
    label: 'Students',
    icon: (
      <svg {...iconProps}>
        <circle cx="9" cy="8" r="3.5" />
        <path d="M3 20a6 6 0 0 1 12 0" />
        <path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 20a6 6 0 0 0-3-5.2" />
      </svg>
    ),
  },
  {
    to: '/app/calendar',
    label: 'Calendar',
    icon: (
      <svg {...iconProps}>
        <rect x="3" y="4.5" width="18" height="16" rx="3" />
        <path d="M3 9h18M8 2.5V6M16 2.5V6" />
      </svg>
    ),
  },
  {
    to: '/app/payments',
    label: 'Payments',
    icon: (
      <svg {...iconProps}>
        <rect x="3" y="5" width="18" height="14" rx="3" />
        <path d="M3 9.5h18M7 14.5h4" />
      </svg>
    ),
  },
  {
    to: '/app/notes',
    label: 'Notes',
    icon: (
      <svg {...iconProps}>
        <path d="M5 3h11l3 3v15H5z" />
        <path d="M9 8h6M9 12h6M9 16h3" />
      </svg>
    ),
  },
  {
    to: '/app/settings',
    label: 'Settings',
    icon: (
      <svg {...iconProps}>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2.5v2.5M12 19v2.5M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2.5 12H5M19 12h2.5M4.2 19.8 6 18M18 6l1.8-1.8" />
      </svg>
    ),
  },
]
