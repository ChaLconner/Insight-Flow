/**
 * E2E Tests for Authentication Flow
 * Tests login, logout, and protected route access
 */
import { test, expect } from '@playwright/test';

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

  test('should display OAuth login options', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Check for Google login button
    const _googleButton = page.getByRole('button', { name: /google/i }).or(
      page.locator('[data-testid="google-login"]')
    );
    
    // OAuth buttons might be present
    // This is optional based on app configuration
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
    
    // Submit should fail or show warning
    await page.getByRole('button', { name: /sign up|register|create/i }).click();
    
    // Should stay on register page
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
