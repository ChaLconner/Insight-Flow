/**
 * Authentication Setup for Playwright
 * Creates authenticated state for tests that require login
 */
import { test as setup, expect } from '@playwright/test';
import * as path from 'path';

const AUTH_FILE = path.join(__dirname, '.auth/user.json');

setup('authenticate', async ({ page }) => {
  // Navigate to login
  await page.goto('/auth/login');
  await page.waitForLoadState('networkidle');

  // Check if already logged in
  if (page.url().includes('/dashboard')) {
    await page.context().storageState({ path: AUTH_FILE });
    return;
  }

  // For test environment, you would use test credentials
  // This is a setup that prepares the storage state
  // In a real scenario, you'd have test user credentials
  
  // Example (uncomment and modify with real test credentials):
  // await page.getByRole('textbox', { name: /email/i }).fill('test@example.com');
  // await page.locator('input[type="password"]').fill('testpassword123');
  // await page.getByRole('button', { name: /sign in|login/i }).click();
  // await expect(page).toHaveURL(/dashboard/);
  
  // Save the authenticated state
  await page.context().storageState({ path: AUTH_FILE });
});
