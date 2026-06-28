import { createContext } from 'react'
import type {
  LoginPayload,
  Org,
  RegisterPayload,
  User,
} from '@/lib/types'

export interface AuthContextValue {
  user: User | null
  org: Org | null
  /** True while the initial /auth/me bootstrap is in flight. */
  loading: boolean
  isAuthenticated: boolean
  login: (payload: LoginPayload) => Promise<void>
  register: (payload: RegisterPayload) => Promise<void>
  logout: () => void
  /** Replace the cached org (e.g. after a settings PATCH). */
  setOrg: (org: Org) => void
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)
