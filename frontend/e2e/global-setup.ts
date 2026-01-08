/**
 * Global Setup for Playwright E2E Tests
 * Handles authentication state preparation
 */
import { chromium, FullConfig } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const AUTH_FILE = path.join(__dirname, '.auth/user.json');

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
    
    // Check if we're already logged in (redirected to dashboard)
    if (page.url().includes('/dashboard')) {
      console.log('Already authenticated');
      await context.storageState({ path: AUTH_FILE });
      await browser.close();
      return;
    }

    // Note: For real authentication, you would fill in actual test credentials
    // This is a placeholder that creates an empty auth state for unauthenticated tests
    console.log('Creating unauthenticated state for public page tests');
    
    // Save the storage state (even without auth for now)
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
