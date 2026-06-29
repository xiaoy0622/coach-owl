import { expect, test } from '@playwright/test'
import { mockActivationApi } from './support/mockApi'

/**
 * Critical activation flow (DoD smoke):
 *
 *   register → land in app → onboarding: org → student → first lesson → done
 *
 * Drives the real UI end-to-end. The API is stubbed at the network layer
 * (see support/mockApi.ts) so the test is deterministic and needs only the
 * Vite dev server — no FastAPI / Postgres. Data is unique per run (timestamped
 * email) and every transition is awaited via a visible heading, never a sleep.
 */
test('activation flow: register, set up studio, add student, schedule first lesson', async ({
  page,
}) => {
  const { email } = await mockActivationApi(page)
  const password = 'sup3rsecret!'

  // --- Register -------------------------------------------------------------
  await page.goto('/register')
  await expect(
    page.getByRole('heading', { name: 'Start free' }),
  ).toBeVisible()

  await page.getByLabel('Your name').fill('E2E Coach')
  await page.getByLabel('Studio name').fill('E2E Studio')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Create my account' }).click()

  // Lands in the authenticated app shell.
  await expect(page).toHaveURL(/\/app$/)
  await expect(
    page.getByRole('heading', { name: /Welcome back/ }),
  ).toBeVisible()

  // --- Onboarding wizard (URL-addressable) ----------------------------------
  await page.goto('/app/onboarding')

  // Step 1: Studio / org setup.
  await expect(
    page.getByRole('heading', { name: 'Set up your studio' }),
  ).toBeVisible()
  await page.getByLabel('Studio name').fill('E2E Studio')
  await page.getByRole('button', { name: 'Save & continue' }).click()

  // Step 2: first student.
  await expect(
    page.getByRole('heading', { name: 'Add your first student' }),
  ).toBeVisible()
  await page.getByLabel('Full name').fill('Ada Lovelace')
  await page.getByRole('button', { name: 'Add & continue' }).click()

  // Step 3: first lesson (date/time are pre-filled by the step).
  await expect(
    page.getByRole('heading', { name: 'Schedule your first lesson' }),
  ).toBeVisible()
  // The booking summary should reflect the student we just created.
  await expect(page.getByText('Ada Lovelace', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Schedule & finish' }).click()

  // Done: activation complete.
  await expect(
    page.getByRole('heading', { name: "You're all set" }),
  ).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Go to dashboard' }),
  ).toBeVisible()
})
