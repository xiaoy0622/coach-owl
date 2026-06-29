import type { Page, Route } from '@playwright/test'

/**
 * Network-level stub for the CoachOwl API.
 *
 * The activation-flow e2e exercises the REAL UI (register → onboarding org →
 * student → lesson → done) but intercepts every `/api/v1/**` request and serves
 * canned responses. This keeps the test fully deterministic and self-contained:
 * it needs only the Vite dev server, no FastAPI / Postgres. The shapes here
 * mirror the typed contract in web/src/lib/types.ts and the feature `types.ts`.
 *
 * Why mocked rather than a live backend: the API lives under `api/` and the
 * `npm run test:e2e` verification only boots the Vite server, so a live-API
 * dependency would be flaky and out of scope. To run the same flow against a
 * real backend, start the API on http://localhost:8000 (or set VITE_API_BASE_URL),
 * delete the `mockActivationApi(page)` call from activation.spec.ts, and use a
 * non-stubbed unique email.
 */

const ORG_ID = 'org-e2e'
const USER_ID = 'user-e2e'
const STUDENT_ID = 'student-e2e'
const LESSON_ID = 'lesson-e2e'
const NOW = '2026-01-01T00:00:00Z'

function user(email: string) {
  return {
    id: USER_ID,
    email,
    name: 'E2E Coach',
    role: 'owner',
    orgId: ORG_ID,
  }
}

function org(name: string) {
  return {
    id: ORG_ID,
    name,
    timezone: 'Australia/Sydney',
    currency: 'AUD',
    gstEnabled: false,
    gstRate: 0.1,
  }
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

/**
 * Installs all routes needed for the activation flow. Returns the unique email
 * used for the run so the spec can assert on it if needed.
 */
export async function mockActivationApi(page: Page): Promise<{ email: string }> {
  const email = `e2e+${Date.now()}@coachowl.test`

  // Catch-all registered FIRST so the specific routes below win (Playwright
  // matches the most recently registered route). Covers incidental dashboard
  // reads (lessons/payments/students lists) with a harmless empty page.
  await page.route('**/api/v1/**', (route) =>
    json(route, { items: [], nextCursor: null }),
  )

  await page.route('**/api/v1/auth/register', (route) =>
    json(route, { token: 'e2e-token', user: user(email) }),
  )

  await page.route('**/api/v1/auth/login', (route) =>
    json(route, { token: 'e2e-token', user: user(email) }),
  )

  await page.route('**/api/v1/auth/me', (route) =>
    json(route, { user: user(email), org: org('') }),
  )

  await page.route('**/api/v1/org', (route) =>
    json(route, org('E2E Studio')),
  )

  await page.route('**/api/v1/students', async (route) => {
    if (route.request().method() !== 'POST') {
      return json(route, { items: [], nextCursor: null })
    }
    const body = (route.request().postDataJSON() ?? {}) as { name?: string }
    return json(route, {
      id: STUDENT_ID,
      orgId: ORG_ID,
      name: body.name ?? 'E2E Student',
      email: null,
      phone: null,
      status: 'active',
      tags: [],
      notes: null,
      isMinor: false,
      dateOfBirth: null,
      createdAt: NOW,
      updatedAt: NOW,
    })
  })

  await page.route('**/api/v1/lessons', async (route) => {
    if (route.request().method() !== 'POST') {
      return json(route, { items: [], nextCursor: null })
    }
    const body = (route.request().postDataJSON() ?? {}) as {
      startsAt?: string
      durationMin?: number
      location?: string | null
    }
    return json(route, {
      items: [
        {
          id: LESSON_ID,
          orgId: ORG_ID,
          studentId: STUDENT_ID,
          coachId: USER_ID,
          recurrenceId: null,
          startsAt: body.startsAt ?? NOW,
          durationMin: body.durationMin ?? 60,
          status: 'scheduled',
          location: body.location ?? null,
          meetingUrl: null,
          cancelReason: null,
          creditDeducted: false,
          capacity: 1,
          createdAt: NOW,
          updatedAt: NOW,
        },
      ],
      nextCursor: null,
    })
  })

  return { email }
}
