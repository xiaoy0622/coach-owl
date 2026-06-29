import { expect, test } from '@playwright/test'

/**
 * UI smoke — guards against build/route regressions with zero backend.
 * Pure client behaviour: auth guard redirect, public form rendering, and the
 * 404 route. Deterministic and fast; complements the activation flow.
 */

test('unauthenticated visit to a protected route redirects to /login', async ({
  page,
}) => {
  await page.goto('/app')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible()
})

test('login form renders with email + password and a submit', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByLabel('Email')).toBeVisible()
  await expect(page.getByLabel('Password')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()

  // Client-side input contracts (HTML validation attributes).
  await expect(page.getByLabel('Email')).toHaveAttribute('type', 'email')
  await expect(page.getByLabel('Email')).toHaveAttribute('required', '')
})

test('register form renders all fields with the expected validation contract', async ({
  page,
}) => {
  await page.goto('/register')
  await expect(page.getByLabel('Your name')).toBeVisible()
  await expect(page.getByLabel('Studio name')).toBeVisible()
  await expect(page.getByLabel('Email')).toBeVisible()
  await expect(page.getByLabel('Password')).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Create my account' }),
  ).toBeVisible()

  // Password requires a minimum length; name + email are required.
  await expect(page.getByLabel('Password')).toHaveAttribute('minlength', '8')
  await expect(page.getByLabel('Your name')).toHaveAttribute('required', '')
})

test('navigating between login and register works', async ({ page }) => {
  await page.goto('/login')
  await page.getByRole('link', { name: 'Create an account' }).click()
  await expect(page).toHaveURL(/\/register$/)
  await page.getByRole('link', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/login$/)
})

test('unknown route renders the 404 page', async ({ page }) => {
  await page.goto('/this-route-does-not-exist')
  await expect(
    page.getByRole('heading', { name: 'This page flew the nest' }),
  ).toBeVisible()
  await expect(page.getByText('404')).toBeVisible()
})
