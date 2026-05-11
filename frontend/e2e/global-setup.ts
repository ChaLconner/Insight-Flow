/**
 * Global Setup for Playwright E2E Tests
 * Handles authentication state preparation
 */
import { chromium, FullConfig } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { getPostLoginRedirect } from '../src/lib/auth-redirect';

const AUTH_FILE = path.join(__dirname, '.auth/user.json');
const E2E_EMAIL = process.env.E2E_USER_EMAIL;
const E2E_PASSWORD = process.env.E2E_USER_PASSWORD;
const E2E_USER_ROLE = process.env.E2E_USER_ROLE ?? 'manager';
const expectedRedirectPath = getPostLoginRedirect(E2E_USER_ROLE);

async function globalSetup(config: FullConfig) {
  // Ensure auth directory exists
  const authDir = path.dirname(AUTH_FILE);
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }

  // Skip if auth file already exists and is recent (less than 1 hour old)
  if (fs.existsSync(AUTH_FILE)) {
    const stats = fs.statSync(AUTH_FILE);
    const hourAgo = Date.now() - 60 * 60 * 1000;
    if (stats.mtimeMs > hourAgo) {
      console.log('Using existing auth state');
      return;
    }
  }

  // Create browser and authenticate
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to login page
    const baseURL = config.projects[0]?.use?.baseURL ?? 'http://localhost:3000';
    await page.goto(`${baseURL}/auth/login`);
    
    // Wait for login form to be ready
    await page.waitForLoadState('networkidle');
    
    // Check if we're already logged in (redirected to the role-based landing page)
    if (page.url().includes(expectedRedirectPath)) {
      console.log('Already authenticated');
      await context.storageState({ path: AUTH_FILE });
      await browser.close();
      return;
    }

    if (E2E_EMAIL && E2E_PASSWORD) {
      await page.getByRole('textbox', { name: /email/i }).fill(E2E_EMAIL);
      await page.locator('input[type="password"]').fill(E2E_PASSWORD);
      await page.getByRole('button', { name: /sign in|login/i }).click();
      await page.waitForLoadState('networkidle');
      await page.waitForURL(new RegExp(`${expectedRedirectPath}`));
      console.log(`Created authenticated state for ${E2E_EMAIL}`);
    } else {
      console.log('Creating unauthenticated state for public page tests');
    }

    await context.storageState({ path: AUTH_FILE });
    
  } catch (error) {
    console.log('Global setup completed (auth setup skipped):', error);
    // Create empty auth file to prevent repeated failures
    fs.writeFileSync(AUTH_FILE, JSON.stringify({ cookies: [], origins: [] }));
  } finally {
    await browser.close();
  }
}

export default globalSetup;
