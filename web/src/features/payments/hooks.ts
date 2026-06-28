// TanStack Query hooks for the payments feature.

import { useQuery } from '@tanstack/react-query'
import { ApiError } from '@/lib/api'
import {
  creditsApi,
  invoicesApi,
  paymentsApi,
  studentsApi,
  type Student,
} from '@/features/payments/api'

export const paymentsKeys = {
  payments: ['payments', 'list'] as const,
  overview: ['payments', 'overview'] as const,
  invoices: ['invoices', 'list'] as const,
  invoice: (id: string) => ['invoices', id] as const,
  packs: (studentId?: string) => ['credits', 'packs', studentId ?? 'all'] as const,
  balance: (studentId: string) => ['credits', 'balance', studentId] as const,
  ledger: (studentId: string) => ['credits', 'ledger', studentId] as const,
  students: ['students', 'list'] as const,
}

export function usePayments() {
  return useQuery({
    queryKey: paymentsKeys.payments,
    queryFn: () => paymentsApi.list(),
  })
}

export function useRevenueOverview() {
  return useQuery({
    queryKey: paymentsKeys.overview,
    queryFn: () => paymentsApi.overview(),
  })
}

export function useInvoices() {
  return useQuery({
    queryKey: paymentsKeys.invoices,
    queryFn: () => invoicesApi.list(),
  })
}

export function usePacks(studentId?: string) {
  return useQuery({
    queryKey: paymentsKeys.packs(studentId),
    queryFn: () => creditsApi.listPacks(studentId),
  })
}

export function useBalance(studentId: string | undefined) {
  return useQuery({
    queryKey: paymentsKeys.balance(studentId ?? ''),
    queryFn: () => creditsApi.balance(studentId as string),
    enabled: Boolean(studentId),
  })
}

export function useLedger(studentId: string | undefined) {
  return useQuery({
    queryKey: paymentsKeys.ledger(studentId ?? ''),
    queryFn: () => creditsApi.ledger(studentId as string),
    enabled: Boolean(studentId),
  })
}

export interface StudentsResult {
  students: Student[]
  /** True when the students endpoint isn't available yet (501). */
  unavailable: boolean
  isLoading: boolean
}

/**
 * Students directory for the pickers. If the students domain isn't live yet
 * the API answers 501 — we surface `unavailable` so the UI can fall back to a
 * manual student-ID field instead of breaking.
 */
export function useStudents(): StudentsResult {
  const query = useQuery({
    queryKey: paymentsKeys.students,
    queryFn: () => studentsApi.list(),
    retry: false,
  })
  const unavailable =
    query.isError &&
    query.error instanceof ApiError &&
    (query.error.status === 501 || query.error.status === 404)
  return {
    students: query.data?.items ?? [],
    unavailable: Boolean(unavailable),
    isLoading: query.isLoading,
  }
}
