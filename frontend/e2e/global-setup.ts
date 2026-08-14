/**
 * Global Setup for Playwright E2E Tests
 * Handles authentication state preparation
 */
import {
  chromium,
  firefox,
  webkit,
  type BrowserContextOptions,
  type FullConfig,
  type FullProject,
} from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { getPostLoginRedirect } from '../src/lib/auth-redirect';

const AUTH_FILE = path.join(__dirname, '.auth/user.json');
const E2E_EMAIL = process.env.E2E_USER_EMAIL;
const E2E_PASSWORD = process.env.E2E_USER_PASSWORD;
const E2E_USER_ROLE = process.env.E2E_USER_ROLE ?? 'manager';
const expectedRedirectPath = getPostLoginRedirect(E2E_USER_ROLE);

function getAuthFile(project: FullProject) {
  const storageState = project.use.storageState;
  return typeof storageState === 'string'
    ? path.resolve(process.cwd(), storageState)
    : AUTH_FILE;
}

function getContextOptions(project: FullProject): BrowserContextOptions {
  const use = project.use;
  return {
    acceptDownloads: use.acceptDownloads,
    baseURL: use.baseURL,
    bypassCSP: use.bypassCSP,
    colorScheme: use.colorScheme,
    deviceScaleFactor: use.deviceScaleFactor,
    extraHTTPHeaders: use.extraHTTPHeaders,
    geolocation: use.geolocation,
    hasTouch: use.hasTouch,
    httpCredentials: use.httpCredentials,
    ignoreHTTPSErrors: use.ignoreHTTPSErrors,
    isMobile: use.isMobile,
    javaScriptEnabled: use.javaScriptEnabled,
    locale: use.locale,
    permissions: use.permissions,
    proxy: use.proxy,
    reducedMotion: use.reducedMotion,
    screen: use.screen,
    serviceWorkers: use.serviceWorkers,
    timezoneId: use.timezoneId,
    userAgent: use.userAgent,
    viewport: use.viewport,
  };
}

function writeEmptyAuthState(authFile: string) {
  fs.mkdirSync(path.dirname(authFile), { recursive: true });
  fs.writeFileSync(authFile, JSON.stringify({ cookies: [], origins: [] }));
}

async function createProjectAuthState(config: FullConfig, project: FullProject) {
  const browserTypes = { chromium, firefox, webkit };
  const browserName = project.use.browserName ?? project.use.defaultBrowserType;
  const browserType = browserTypes[browserName];
  const browser = await browserType.launch({
    ...project.use.launchOptions,
    channel: project.use.channel,
    headless: project.use.headless,
  });
  const context = await browser.newContext(getContextOptions(project));
  const page = await context.newPage();

  try {
    const baseURL = project.use.baseURL ?? config.use.baseURL ?? 'http://localhost:3000';
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

    const authFile = getAuthFile(project);
    fs.mkdirSync(path.dirname(authFile), { recursive: true });
    await context.storageState({ path: authFile });
    console.log(`Created authenticated state for ${E2E_EMAIL} (${project.name})`);
  } finally {
    await browser.close();
  }
}

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
    writeEmptyAuthState(AUTH_FILE);
    for (const project of config.projects) {
      writeEmptyAuthState(getAuthFile(project));
    }
    console.log('No E2E credentials configured; protected tests must be skipped');
    return;
  }

  try {
    for (const project of config.projects) {
      await createProjectAuthState(config, project);
    }
  } catch (error) {
    console.error('Global E2E authentication setup failed:', error);
    throw error;
  }
}

export default globalSetup;
