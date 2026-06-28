# CoachOwl — Web (app shell)

The React front end for CoachOwl. Built with **Vite + React + TypeScript +
Tailwind CSS**, **TanStack Query** for server state, and **React Router v6** for
URL-addressable navigation.

This is the Wave 0–1 foundation: scaffold, typed API client, auth flow, the
protected app shell, and the design-system primitives. Wave 2 domain pages
(Students, Calendar, Payments) plug into the routes that already exist.

## Prerequisites

- Node 20+ (developed on Node 24, npm 11)
- The CoachOwl API running at `http://localhost:8000` (see `../api`)

## Setup

```bash
cd web
npm install
cp .env.example .env   # adjust VITE_API_BASE_URL if your API isn't on :8000
```

## Scripts

| Command           | What it does                                          |
| ----------------- | ----------------------------------------------------- |
| `npm run dev`     | Vite dev server on **http://localhost:5173**          |
| `npm run build`   | `tsc -b` typecheck **+** `vite build` production build |
| `npm run lint`    | ESLint (flat config, typescript-eslint)               |
| `npm run preview` | Serve the production build on port 5173               |

> The dev server is pinned to port **5173** (`strictPort`) because other dev
> servers in this environment use 3000.

## Environment

| Variable             | Default                 | Purpose                        |
| -------------------- | ----------------------- | ------------------------------ |
| `VITE_API_BASE_URL`  | `http://localhost:8000` | Base URL the API client calls. |

## Architecture

### URL-based navigation (mandatory)

Every view is a route. Navigation uses `<Link>` / `<NavLink>` / `useNavigate`,
never in-place state view-switching. Routes are deep-linkable and refresh-safe.

| Path             | Screen                                   | Auth      |
| ---------------- | ---------------------------------------- | --------- |
| `/`              | Redirect → `/app`                        | —         |
| `/login`         | Sign in (real `POST /auth/login`)        | public    |
| `/register`      | Sign up (real `POST /auth/register`)     | public    |
| `/app`           | Dashboard (today / stats / quick links)  | protected |
| `/app/students`  | Students (Wave 2 placeholder)            | protected |
| `/app/calendar`  | Calendar (Wave 2 placeholder)            | protected |
| `/app/payments`  | Payments (Wave 2 placeholder)            | protected |
| `/app/settings`  | Org settings — live `PATCH /api/v1/org`  | protected |
| `*`              | 404                                      | —         |

The `/app` subtree is wrapped in `<RequireAuth>`: while `/auth/me` bootstraps it
shows a spinner; unauthenticated visitors are redirected to `/login` (preserving
the intended destination so they bounce back after signing in).

### Auth & token flow

- `src/lib/api.ts` — typed `fetch` wrapper. Prefixes `VITE_API_BASE_URL`,
  injects `Authorization: Bearer <jwt>`, normalizes errors into `ApiError`
  (`status` / `code` / `message`). On **401** it clears the token and dispatches
  a `coachowl:unauthorized` event.
- `src/auth/AuthProvider.tsx` — holds `user` + `org`. On boot, if a token is in
  `localStorage` it hydrates the session from `GET /auth/me`. `login` / `register`
  store the token then hydrate. It listens for `coachowl:unauthorized` and drops
  the session (route guard then redirects to `/login`).
- `src/auth/useAuth.ts` — `{ user, org, loading, isAuthenticated, login,
  register, logout, setOrg }`.

The JWT is persisted in `localStorage` under `coachowl.token`.

### Design system

`src/components/ui/` mirrors the marketing landing page (palette + Nunito /
Nunito Sans, loaded via `index.html`):

`Button` (primary amber / secondary outline / ghost / danger), `Input`,
`Select`, `Toggle`, `Card` + `CardHeader`, `Spinner`, `EmptyState`,
`InlineError`, and a `Toast` system (`ToastProvider` + `useToast`). The owl mark
lives in `src/components/Logo.tsx` and `public/owl.svg`.

Tailwind theme tokens are in `tailwind.config.js` (`brand.*`, `amber.*`,
`cream`, `ink`, `muted`, fonts `font-display` / `font-sans`).

## Where Wave 2 plugs in

- **New domain page:** add the screen under `src/pages/`, add a `<Route>` in
  `src/App.tsx`, and (if it's a top-level destination) an entry in
  `src/components/nav-items.tsx`. Replace the `domain-pages.tsx` placeholders
  in place — the routes already exist.
- **API calls:** use the `api` client from `src/lib/api.ts` and wrap reads in
  TanStack Query (`queryClient` is already provided at the root). Add request/
  response types to `src/lib/types.ts`.
- **Sub-routes** (e.g. `/app/students/:id`, `/app/calendar?view=week`) nest
  under the existing `/app` layout route.
