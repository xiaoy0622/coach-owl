import { useCallback, useEffect, useState } from 'react'
import { clearToken, getToken, setToken, UNAUTHORIZED_EVENT } from '@/lib/api'
import { queryClient } from '@/lib/queryClient'
import type {
  LoginPayload,
  Org,
  RegisterPayload,
  User,
} from '@/lib/types'
import { authApi } from '@/auth/authApi'
import { AuthContext, type AuthContextValue } from '@/auth/context'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [org, setOrgState] = useState<Org | null>(null)
  const [loading, setLoading] = useState<boolean>(() => Boolean(getToken()))

  const resetSession = useCallback(() => {
    clearToken()
    setUser(null)
    setOrgState(null)
    queryClient.clear()
  }, [])

  // Bootstrap: if a token is persisted, hydrate the session from /auth/me.
  useEffect(() => {
    if (!getToken()) {
      setLoading(false)
      return
    }
    const controller = new AbortController()
    authApi
      .me(controller.signal)
      .then(({ user, org }) => {
        setUser(user)
        setOrgState(org)
      })
      .catch(() => {
        // Invalid/expired token (or the 401 handler already cleared it).
        resetSession()
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [resetSession])

  // A 401 from any request drops the session; route guards then redirect.
  useEffect(() => {
    const onUnauthorized = () => {
      setUser(null)
      setOrgState(null)
      queryClient.clear()
    }
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [])

  const hydrate = useCallback(async (token: string) => {
    setToken(token)
    const { user, org } = await authApi.me()
    setUser(user)
    setOrgState(org)
  }, [])

  const login = useCallback(
    async (payload: LoginPayload) => {
      const { token } = await authApi.login(payload)
      await hydrate(token)
    },
    [hydrate],
  )

  const register = useCallback(
    async (payload: RegisterPayload) => {
      const { token } = await authApi.register(payload)
      await hydrate(token)
    },
    [hydrate],
  )

  const value: AuthContextValue = {
    user,
    org,
    loading,
    isAuthenticated: Boolean(user),
    login,
    register,
    logout: resetSession,
    setOrg: setOrgState,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
