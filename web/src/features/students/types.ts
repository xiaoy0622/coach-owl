// Students / CRM contract types (mirror api/app/schemas/{students,guardians,imports}.py).
// Response keys are camelCase (see Execution-Plan §5).

export type StudentStatus = 'active' | 'paused' | 'churned'

export interface Student {
  id: string
  orgId: string
  name: string
  email: string | null
  phone: string | null
  status: StudentStatus
  tags: string[]
  notes: string | null
  createdAt: string
  updatedAt: string
}

export interface StudentCreate {
  name: string
  email?: string | null
  phone?: string | null
  status?: StudentStatus
  tags?: string[]
  notes?: string | null
}

export type StudentUpdate = Partial<StudentCreate>

export interface Guardian {
  id: string
  orgId: string
  studentId: string
  name: string
  relationship: string | null
  email: string | null
  phone: string | null
  isPrimary: boolean
  createdAt: string
  updatedAt: string
}

export interface GuardianCreate {
  studentId: string
  name: string
  relationship?: string | null
  email?: string | null
  phone?: string | null
  isPrimary?: boolean
}

export type GuardianUpdate = Partial<Omit<GuardianCreate, 'studentId'>>

export interface Page<T> {
  items: T[]
  nextCursor: string | null
}

// ---- Smart import ----------------------------------------------------------
export type ImportJobStatus = 'parsing' | 'review' | 'committed' | 'discarded'

export interface ImportGuardianCandidate {
  name: string
  relationship?: string | null
  email?: string | null
  phone?: string | null
  isPrimary?: boolean
}

export interface ImportCandidate {
  name: string
  email: string | null
  phone: string | null
  status: StudentStatus
  tags: string[]
  notes: string | null
  scheduleText: string | null
  guardians: ImportGuardianCandidate[]
  confidence: number
  warnings: string[]
  /** UI-only: when true the candidate is excluded from commit. */
  skip?: boolean
}

export interface ImportParsed {
  source: string
  delimiter?: string
  columns: string[]
  candidates: ImportCandidate[]
  createdStudentIds?: string[]
}

export interface ImportJob {
  id: string
  orgId: string
  rawInput: string
  parsed: ImportParsed
  status: ImportJobStatus
  createdAt: string
}

export interface ListParams {
  search?: string
  status?: StudentStatus | ''
  tag?: string
  cursor?: string
  limit?: number
}
