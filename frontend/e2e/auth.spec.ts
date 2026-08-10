/**
 * E2E Tests for Authentication Flow
 * Tests login, logout, and protected route access
 */
import { test, expect, type Page } from '@playwright/test';
import { getPostLoginRedirect } from '../src/lib/auth-redirect';

const E2E_EMAIL = process.env.E2E_USER_EMAIL;
const E2E_PASSWORD = process.env.E2E_USER_PASSWORD;
const E2E_USER_ROLE = process.env.E2E_USER_ROLE ?? 'manager';
const expectedRedirectPath = getPostLoginRedirect(E2E_USER_ROLE);
const baseURL = process.env.BASE_URL ?? 'http://localhost:3000';
const hasE2EAuth = Boolean(E2E_EMAIL && E2E_PASSWORD);

async function loginWithE2ECredentials(page: Page) {
  await page.goto('/auth/login');
  await page.getByRole('textbox', { name: /email/i }).fill(E2E_EMAIL ?? '');
  await page.locator('input[type="password"]').fill(E2E_PASSWORD ?? '');
  await page.getByRole('button', { name: /sign in|login/i }).click();

  const expectedUrl = new URL(expectedRedirectPath, baseURL);
  await page.waitForURL((url) =>
    url.pathname === expectedUrl.pathname &&
    (!expectedUrl.search || url.search === expectedUrl.search),
    { timeout: 15000 },
  );
}

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any existing auth state
    await page.context().clearCookies();
  });

  test('should display login page', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Check page title
    await expect(page).toHaveTitle(/Login|Insight Flow/);
    
    // Check for login form elements
    await expect(page.getByRole('textbox', { name: /email/i })).toBeVisible();
    await expect(page.getByRole('textbox', { name: /password/i }).or(page.locator('input[type="password"]'))).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in|login/i })).toBeVisible();
  });

  test('should show validation errors for empty form', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Click login without filling form
    await page.getByRole('button', { name: /sign in|login/i }).click();
    
    // Should show validation errors or stay on login page
    await expect(page).toHaveURL(/login/);
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Fill in invalid credentials
    await page.getByRole('textbox', { name: /email/i }).fill('invalid@example.com');
    await page.locator('input[type="password"]').fill('wrongpassword');
    
    // Submit form
    await page.getByRole('button', { name: /sign in|login/i }).click();
    
    // Should show error message or stay on login page
    await expect(page).toHaveURL(/login/);
  });

  test('should redirect to login when accessing protected route', async ({ page }) => {
    // Try to access protected route without auth
    await page.goto('/dashboard');
    
    // Should redirect to login
    await expect(page).toHaveURL(/login/);
  });

  test('should display register link', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Check for register link
    const registerLink = page.getByRole('link', { name: /register|sign up|create account/i });
    await expect(registerLink).toBeVisible();
  });

  test('should display forgot password link', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Check for forgot password link
    const forgotLink = page.getByRole('link', { name: /forgot|reset password/i });
    await expect(forgotLink).toBeVisible();
  });

  test('should display OAuth login options if configured', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Check for Google login button
    const googleButton = page.getByRole('button', { name: /google/i }).or(
      page.locator('[data-testid="google-login"]')
    );
    
    // OAuth buttons are optional based on app configuration
    const hasOAuth = await googleButton.isVisible().catch(() => false);
    if (hasOAuth) {
      await expect(googleButton).toBeVisible();
    } else {
      // Skip assertion if OAuth is not configured
      test.info().annotations.push({ type: 'skip', description: 'OAuth not configured' });
    }
  });

  test('should successfully login with valid credentials', async ({ page }) => {
    test.skip(!E2E_EMAIL || !E2E_PASSWORD, 'E2E credentials are not configured');

    await loginWithE2ECredentials(page);
  });

  test('should logout successfully when authenticated', async ({ page }) => {
    test.skip(!hasE2EAuth, 'E2E credentials are not configured');

    // beforeEach clears storageState cookies, so establish a fresh session first.
    await loginWithE2ECredentials(page);
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Look for logout button
    const logoutButton = page.getByRole('button', { name: /logout|sign out/i }).or(
      page.locator('[data-testid="logout-button"]')
    );
    
    await expect(logoutButton).toBeVisible();
    await logoutButton.click();

    await expect(page).toHaveURL(/login/);
  });
});

test.describe('Register Flow', () => {
  test('should display register page', async ({ page }) => {
    await page.goto('/auth/register');
    
    // Check for register form elements
    await expect(page.getByRole('textbox', { name: /email/i })).toBeVisible();
    await expect(page.locator('input[type="password"]').first()).toBeVisible();
    await expect(page.getByRole('button', { name: /sign up|register|create/i })).toBeVisible();
  });

  test('should show validation for weak password', async ({ page }) => {
    await page.goto('/auth/register');
    
    // Fill form with weak password
    await page.getByRole('textbox', { name: /name/i }).first().fill('Test User');
    await page.getByRole('textbox', { name: /email/i }).fill('test@example.com');
    await page.locator('input[type="password"]').first().fill('123');
    
    // Wait for validation
    await page.waitForTimeout(500);
    
    const submitButton = page.getByRole('button', { name: /sign up|register|create/i });
    
    // Either button should be disabled OR validation error should be shown
    const isDisabled = await submitButton.isDisabled();
    const hasValidationError = await page.locator('[class*="error"], [class*="invalid"], [role="alert"]').count() > 0;
    
    // If button is not disabled, try clicking and verify we stay on register page
    if (!isDisabled && !hasValidationError) {
      await submitButton.click({ timeout: 5000 }).catch(() => {});
    }
    
    // Should stay on register page (form validation prevents navigation)
    await expect(page).toHaveURL(/register/);
  });
});

test.describe('Password Reset Flow', () => {
  test('should display forgot password page', async ({ page }) => {
    await page.goto('/auth/forgot-password');
    
    // Check for email input
    await expect(page.getByRole('textbox', { name: /email/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /reset|send|submit/i })).toBeVisible();
  });
});
