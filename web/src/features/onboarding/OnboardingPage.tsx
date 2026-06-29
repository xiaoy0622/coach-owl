import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import type { Student } from '@/features/students/types'
import { StepIndicator } from './StepIndicator'
import { OrgStep } from './steps/OrgStep'
import { StudentStep } from './steps/StudentStep'
import { LessonStep } from './steps/LessonStep'
import { DoneStep } from './steps/DoneStep'
import {
  clearProgress,
  loadProgress,
  saveProgress,
  STEP_ORDER,
  type OnboardingProgress,
  type OnboardingStepId,
} from './storage'

/**
 * Guided activation wizard — Studio → Student → First lesson → Done.
 *
 * URL-addressable at /app/onboarding. Progress (current step + the created
 * student) is persisted to localStorage on every transition, so a refresh or a
 * return visit resumes exactly where the coach left off. Every step is
 * skippable.
 */
export function OnboardingPage() {
  // Seed from persisted progress so a refresh resumes mid-wizard.
  const [progress, setProgress] = useState<OnboardingProgress>(() => loadProgress())

  const update = useCallback((next: OnboardingProgress) => {
    setProgress(next)
    saveProgress(next)
  }, [])

  const goTo = useCallback(
    (step: OnboardingStepId) => update({ ...progress, step }),
    [progress, update],
  )

  const nextOf = (step: OnboardingStepId): OnboardingStepId => {
    const idx = STEP_ORDER.indexOf(step)
    return STEP_ORDER[Math.min(idx + 1, STEP_ORDER.length - 1)]
  }

  const advance = useCallback(
    () => goTo(nextOf(progress.step)),
    [goTo, progress.step],
  )

  const handleStudentCreated = useCallback(
    (student: Student) =>
      update({
        ...progress,
        step: 'lesson',
        studentId: student.id,
        studentName: student.name,
      }),
    [progress, update],
  )

  const restart = useCallback(() => {
    clearProgress()
    const fresh: OnboardingProgress = {
      step: 'org',
      studentId: null,
      studentName: null,
    }
    setProgress(fresh)
  }, [])

  return (
    <>
      <PageHeader
        title="Get started"
        description="Three quick steps to get your studio running — under ten minutes."
        action={
          <Link
            to="/app"
            className="co-focus rounded-lg text-sm font-semibold text-muted hover:text-ink-deep"
          >
            Skip setup
          </Link>
        }
      />

      <StepIndicator current={progress.step} />

      {progress.step === 'org' && (
        <OrgStep onNext={advance} onSkip={advance} />
      )}

      {progress.step === 'student' && (
        <StudentStep onCreated={handleStudentCreated} onSkip={advance} />
      )}

      {progress.step === 'lesson' && (
        <LessonStep
          studentId={progress.studentId}
          studentName={progress.studentName}
          onScheduled={advance}
          onSkip={advance}
          onBack={() => goTo('student')}
        />
      )}

      {progress.step === 'done' && <DoneStep onRestart={restart} />}
    </>
  )
}
