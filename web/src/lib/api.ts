// Typed fetch wrapper for the CoachOwl API.
//
//  - Prefixes every request with VITE_API_BASE_URL (default http://localhost:8000).
//  - Injects the persisted JWT as `Authorization: Bearer <token>`.
//  - Parses the backend's `{ error: { code, message, details? } }` body into a
//    normalized ApiError so callers can branch on `status` / `code`.
//  - On 401 it clears the token and broadcasts `coachowl:unauthorized` so the
//    AuthProvider can drop the session and the router can redirect to /login.

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const TOKEN_KEY = 'coachowl.token'
export const UNAUTHORIZED_EVENT = 'coachowl:unauthorized'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export interface ApiErrorShape {
  code: string
  message: string
  details?: unknown
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details?: unknown

  constructor(status: number, shape: ApiErrorShape) {
    super(shape.message)
    this.name = 'ApiError'
    this.status = status
    this.code = shape.code
    this.details = shape.details
  }
}

type Method = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'

interface RequestOptions {
  /** Skip attaching the Authorization header (used for login/register). */
  auth?: boolean
  signal?: AbortSignal
}

async function request<TResponse>(
  method: Method,
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<TResponse> {
  const { auth = true, signal } = options

  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  if (auth) {
    const token = getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  let res: Response
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    })
  } catch {
    // Network / CORS / connection-refused — surface a consistent shape.
    throw new ApiError(0, {
      code: 'network_error',
      message: 'Could not reach the server. Check your connection and try again.',
    })
  }

  if (res.status === 401) {
    clearToken()
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
  }

  // 204 No Content
  if (res.status === 204) {
    return undefined as TResponse
  }

  const raw = await res.text()
  const data = raw ? safeJsonParse(raw) : undefined

  if (!res.ok) {
    const shape = extractError(data)
    throw new ApiError(res.status, shape)
  }

  return data as TResponse
}

function safeJsonParse(raw: string): unknown {
  try {
    return JSON.parse(raw)
  } catch {
    return undefined
  }
}

function extractError(data: unknown): ApiErrorShape {
  if (
    data &&
    typeof data === 'object' &&
    'error' in data &&
    (data as { error: unknown }).error &&
    typeof (data as { error: unknown }).error === 'object'
  ) {
    const err = (data as { error: Partial<ApiErrorShape> }).error
    return {
      code: err.code ?? 'error',
      message: err.message ?? 'Something went wrong.',
      details: err.details,
    }
  }
  return { code: 'error', message: 'Something went wrong. Please try again.' }
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>('GET', path, undefined, options),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>('POST', path, body, options),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>('PATCH', path, body, options),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>('PUT', path, body, options),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>('DELETE', path, undefined, options),
}
