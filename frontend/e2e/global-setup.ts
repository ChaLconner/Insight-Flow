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

  const hasCredentials = Boolean(E2E_EMAIL && E2E_PASSWORD);

  if (Boolean(E2E_EMAIL) !== Boolean(E2E_PASSWORD)) {
    throw new Error('E2E_USER_EMAIL and E2E_USER_PASSWORD must be configured together');
  }

  if (!hasCredentials) {
    // Never reuse a previous authenticated state when credentials are absent.
    // Protected tests must skip instead of inheriting an unknown session.
    fs.writeFileSync(AUTH_FILE, JSON.stringify({ cookies: [], origins: [] }));
    console.log('No E2E credentials configured; protected tests must be skipped');
    return;
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
    
    await page.getByRole('textbox', { name: /email/i }).fill(E2E_EMAIL as string);
    await page.locator('input[type="password"]').fill(E2E_PASSWORD as string);
    await page.getByRole('button', { name: /sign in|login/i }).click();
    await page.waitForLoadState('networkidle');
    const expectedUrl = new URL(expectedRedirectPath, baseURL);
    await page.waitForURL((url) =>
      url.pathname === expectedUrl.pathname &&
      (!expectedUrl.search || url.search === expectedUrl.search),
    );
    console.log(`Created authenticated state for ${E2E_EMAIL}`);

    await context.storageState({ path: AUTH_FILE });
    
  } catch (error) {
    console.error('Global E2E authentication setup failed:', error);
    throw error;
  } finally {
    await browser.close();
  }
}

export default globalSetup;
