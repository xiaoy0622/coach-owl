// Resumable onboarding progress, persisted to localStorage so a refresh or a
// return visit continues exactly where the coach left off (CO-W03 acceptance).

export type OnboardingStepId = 'org' | 'student' | 'lesson' | 'done'

export const STEP_ORDER: OnboardingStepId[] = ['org', 'student', 'lesson', 'done']

export interface OnboardingProgress {
  /** The step the wizard should resume on. */
  step: OnboardingStepId
  /** The student created in step 2 (so step 3 can pre-select them). */
  studentId: string | null
  studentName: string | null
}

const STORAGE_KEY = 'coachowl.onboarding'

const DEFAULT_PROGRESS: OnboardingProgress = {
  step: 'org',
  studentId: null,
  studentName: null,
}

function isStepId(value: unknown): value is OnboardingStepId {
  return (
    typeof value === 'string' &&
    (STEP_ORDER as string[]).includes(value)
  )
}

export function loadProgress(): OnboardingProgress {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...DEFAULT_PROGRESS }
    const parsed = JSON.parse(raw) as Partial<OnboardingProgress>
    return {
      step: isStepId(parsed.step) ? parsed.step : 'org',
      studentId: typeof parsed.studentId === 'string' ? parsed.studentId : null,
      studentName:
        typeof parsed.studentName === 'string' ? parsed.studentName : null,
    }
  } catch {
    return { ...DEFAULT_PROGRESS }
  }
}

export function saveProgress(progress: OnboardingProgress): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress))
  } catch {
    // Quota / privacy-mode failures are non-fatal — the wizard still works in
    // memory for this session; it just won't resume after a refresh.
  }
}

export function clearProgress(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}
