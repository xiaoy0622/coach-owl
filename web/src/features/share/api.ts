// Public share-page data access — deliberately UNAUTHENTICATED.
//
// This endpoint resolves a bare share token to one student's read-only
// schedule + balance and must work with NO token/session. The shared `api`
// client injects auth + broadcasts `coachowl:unauthorized` on 401, neither of
// which we want on a public page, so we use a tiny standalone fetch here.

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export interface PublicLesson {
  startsAt: string // ISO8601 UTC
  durationMin: number
  location: string | null
  meetingUrl: string | null
}

export interface PublicShare {
  studentName: string
  timezone: string // org timezone — render all times in this zone
  creditBalance: number
  upcomingLessons: PublicLesson[]
}

/** Why a public share couldn't be shown — drives the page's empty states. */
export type ShareErrorKind = 'expired' | 'not_found' | 'network'

export class ShareError extends Error {
  readonly kind: ShareErrorKind
  constructor(kind: ShareErrorKind, message: string) {
    super(message)
    this.name = 'ShareError'
    this.kind = kind
  }
}

export async function fetchPublicShare(
  token: string,
  signal?: AbortSignal,
): Promise<PublicShare> {
  let res: Response
  try {
    res = await fetch(
      `${BASE_URL}/api/v1/share-links/public/${encodeURIComponent(token)}`,
      { headers: { Accept: 'application/json' }, signal },
    )
  } catch {
    throw new ShareError('network', 'Could not reach the server.')
  }

  if (res.status === 410) {
    throw new ShareError('expired', 'This share link has expired.')
  }
  if (!res.ok) {
    // 404 (revoked/invalid) and anything else fall back to "not found".
    throw new ShareError('not_found', 'This share link is no longer valid.')
  }
  return (await res.json()) as PublicShare
}
