import { api } from '@/lib/api'
import type {
  Guardian,
  GuardianCreate,
  GuardianUpdate,
  ImportJob,
  ImportParsed,
  ListParams,
  Page,
  Student,
  StudentCreate,
  StudentUpdate,
} from './types'

function qs(params: ListParams): string {
  const sp = new URLSearchParams()
  if (params.search) sp.set('search', params.search)
  if (params.status) sp.set('status', params.status)
  if (params.tag) sp.set('tag', params.tag)
  if (params.cursor) sp.set('cursor', params.cursor)
  if (params.limit) sp.set('limit', String(params.limit))
  const s = sp.toString()
  return s ? `?${s}` : ''
}

export const studentsApi = {
  list: (params: ListParams = {}) =>
    api.get<Page<Student>>(`/api/v1/students${qs(params)}`),

  get: (id: string) => api.get<Student>(`/api/v1/students/${id}`),

  create: (body: StudentCreate) =>
    api.post<Student>('/api/v1/students', body),

  update: (id: string, body: StudentUpdate) =>
    api.patch<Student>(`/api/v1/students/${id}`, body),

  remove: (id: string) => api.delete<void>(`/api/v1/students/${id}`),
}

export const guardiansApi = {
  list: (studentId: string) =>
    api.get<Page<Guardian>>(`/api/v1/guardians?studentId=${studentId}`),

  create: (body: GuardianCreate) =>
    api.post<Guardian>('/api/v1/guardians', body),

  update: (id: string, body: GuardianUpdate) =>
    api.patch<Guardian>(`/api/v1/guardians/${id}`, body),

  remove: (id: string) => api.delete<void>(`/api/v1/guardians/${id}`),
}

export const importsApi = {
  parse: (rawInput: string) =>
    api.post<ImportJob>('/api/v1/students/import/parse', { rawInput }),

  get: (jobId: string) =>
    api.get<ImportJob>(`/api/v1/students/import/${jobId}`),

  commit: (jobId: string, parsed: ImportParsed) =>
    api.post<ImportJob>(`/api/v1/students/import/${jobId}/commit`, { parsed }),

  discard: (jobId: string) =>
    api.post<ImportJob>(`/api/v1/students/import/${jobId}/discard`),
}
