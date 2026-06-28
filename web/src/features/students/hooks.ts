import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { guardiansApi, importsApi, studentsApi } from './api'
import type {
  GuardianCreate,
  GuardianUpdate,
  ImportParsed,
  ListParams,
  StudentCreate,
  StudentUpdate,
} from './types'

export const studentKeys = {
  all: ['students'] as const,
  list: (params: ListParams) => ['students', 'list', params] as const,
  detail: (id: string) => ['students', 'detail', id] as const,
  guardians: (studentId: string) => ['guardians', studentId] as const,
  importJob: (jobId: string) => ['import', jobId] as const,
}

export function useStudents(params: ListParams) {
  return useInfiniteQuery({
    queryKey: studentKeys.list(params),
    queryFn: ({ pageParam }: { pageParam: string | undefined }) =>
      studentsApi.list({ ...params, cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
  })
}

export function useStudent(id: string) {
  return useQuery({
    queryKey: studentKeys.detail(id),
    queryFn: () => studentsApi.get(id),
    enabled: Boolean(id),
  })
}

export function useCreateStudent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: StudentCreate) => studentsApi.create(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: studentKeys.all }),
  })
}

export function useUpdateStudent(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: StudentUpdate) => studentsApi.update(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: studentKeys.all })
      qc.invalidateQueries({ queryKey: studentKeys.detail(id) })
    },
  })
}

export function useDeleteStudent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => studentsApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: studentKeys.all }),
  })
}

export function useGuardians(studentId: string) {
  return useQuery({
    queryKey: studentKeys.guardians(studentId),
    queryFn: () => guardiansApi.list(studentId),
    enabled: Boolean(studentId),
  })
}

export function useCreateGuardian(studentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: GuardianCreate) => guardiansApi.create(body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: studentKeys.guardians(studentId) }),
  })
}

export function useUpdateGuardian(studentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: GuardianUpdate }) =>
      guardiansApi.update(id, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: studentKeys.guardians(studentId) }),
  })
}

export function useDeleteGuardian(studentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => guardiansApi.remove(id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: studentKeys.guardians(studentId) }),
  })
}

export function useImportJob(jobId: string) {
  return useQuery({
    queryKey: studentKeys.importJob(jobId),
    queryFn: () => importsApi.get(jobId),
    enabled: Boolean(jobId),
  })
}

export function useParseImport() {
  return useMutation({
    mutationFn: (rawInput: string) => importsApi.parse(rawInput),
  })
}

export function useCommitImport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ jobId, parsed }: { jobId: string; parsed: ImportParsed }) =>
      importsApi.commit(jobId, parsed),
    onSuccess: () => qc.invalidateQueries({ queryKey: studentKeys.all }),
  })
}
