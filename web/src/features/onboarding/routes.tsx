import { Route, Routes } from 'react-router-dom'
import { OnboardingPage } from './OnboardingPage'

/**
 * Onboarding feature sub-router — mounted at /app/onboarding/* (see App.tsx).
 *
 * A single URL-addressable, resumable activation wizard. The current step and
 * the just-created student persist to localStorage, so a refresh or a return
 * visit continues where the coach left off (CO-W03).
 */
export default function OnboardingRoutes() {
  return (
    <Routes>
      <Route index element={<OnboardingPage />} />
    </Routes>
  )
}
