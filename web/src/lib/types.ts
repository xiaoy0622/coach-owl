// Shared API contract types. These mirror the backend auth/org contract
// (see CoachOwl-Execution-Plan-v0.md §5). Response keys are camelCase.

export type Role = 'owner' | 'coach'

export interface User {
  id: string
  email: string
  name: string
  role: Role
  orgId: string
}

export interface Org {
  id: string
  name: string
  timezone: string
  currency: string
  gstEnabled: boolean
  gstRate: number
}

/** GET /api/v1/auth/me */
export interface MeResponse {
  user: User
  org: Org
}

/** POST /api/v1/auth/login | /register */
export interface AuthResponse {
  token: string
  user: User
}

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  email: string
  password: string
  name: string
  orgName?: string
}

export interface OrgUpdatePayload {
  name?: string
  timezone?: string
  currency?: string
  gstEnabled?: boolean
  gstRate?: number
}
