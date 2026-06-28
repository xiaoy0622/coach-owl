import { api } from '@/lib/api'
import type {
  AuthResponse,
  LoginPayload,
  MeResponse,
  Org,
  OrgUpdatePayload,
  RegisterPayload,
} from '@/lib/types'

export const authApi = {
  login: (payload: LoginPayload) =>
    api.post<AuthResponse>('/api/v1/auth/login', payload, { auth: false }),

  register: (payload: RegisterPayload) =>
    api.post<AuthResponse>('/api/v1/auth/register', payload, { auth: false }),

  me: (signal?: AbortSignal) =>
    api.get<MeResponse>('/api/v1/auth/me', { signal }),

  updateOrg: (payload: OrgUpdatePayload) =>
    api.patch<Org>('/api/v1/org', payload),
}
