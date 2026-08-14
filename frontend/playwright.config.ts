import { defineConfig, devices } from '@playwright/test';

const reuseExistingServer = process.env.PLAYWRIGHT_REUSE_SERVER === '1';
const startBackend = process.env.PLAYWRIGHT_START_BACKEND === '1';
const useProductionBuild = process.env.PLAYWRIGHT_PRODUCTION_BUILD === '1';
const authStatePath = (projectName: string) =>
  `./e2e/.auth/${projectName.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.json`;
const frontendServer = {
  command: useProductionBuild
    ? 'cross-env NEXT_PUBLIC_E2E=1 VERCEL=1 npm run build && cross-env NEXT_PUBLIC_E2E=1 VERCEL=1 npm run start'
    : 'cross-env NEXT_PUBLIC_E2E=1 npm run dev',
  url: 'http://localhost:3000',
  reuseExistingServer,
  timeout: 120000,
};

const backendCommand =
  process.platform === 'win32'
    ? 'powershell -NoProfile -Command "Set-Location ..\\backend; $env:HOST=\'127.0.0.1\'; $env:PORT=\'8000\'; $env:RELOAD=\'false\'; python scripts/start.py"'
    : "cd ../backend && HOST=127.0.0.1 PORT=8000 RELOAD=false python scripts/start.py";

const backendServer = {
  command: backendCommand,
  url: 'http://127.0.0.1:8000/health',
  name: 'Backend',
  reuseExistingServer,
  timeout: 120000,
};

/**
 * Playwright E2E Test Configuration for Insight-Flow
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',
  /* Configure snapshot path to be platform agnostic */
  snapshotPathTemplate: './e2e/{testFileDir}/{testFileName}-snapshots/{arg}-{projectName}{ext}',

  
  /* Run tests in files in parallel */
  fullyParallel: true,
  
  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,
  
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  
  /* Opt out of parallel tests on CI */
  workers: process.env.CI ? 1 : undefined,
  
  /* Reporter to use */
  reporter: [
    ['html', { open: 'never' }],
    ['json', { outputFile: 'e2e-results.json' }],
    process.env.CI ? ['github'] : ['line'],
  ],
  
  /* Shared settings for all the projects below */
  use: {
    /* Base URL to use in actions like `await page.goto('/')` */
    baseURL: process.env.BASE_URL ?? 'http://localhost:3000',

    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',
    
    /* Screenshot on failure */
    screenshot: 'only-on-failure',
    
    /* Video on failure */
    video: 'on-first-retry',
    
    /* Maximum time each action can take */
    actionTimeout: 10000,
    
    /* Maximum time for navigation */
    navigationTimeout: 30000,
  },
  
  /* Global timeout for each test */
  timeout: 60000,
  
  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: authStatePath('chromium') },
    },
    
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'], storageState: authStatePath('firefox') },
    },
    
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'], storageState: authStatePath('webkit') },
    },
    
    /* Test against mobile viewports */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'], storageState: authStatePath('mobile-chrome') },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'], storageState: authStatePath('mobile-safari') },
    },
  ],
  
  /* Run your local dev server before starting the tests */
  webServer: startBackend ? [backendServer, frontendServer] : frontendServer,
  
  /* Folder for test artifacts such as screenshots, videos, traces, etc. */
  outputDir: 'e2e-results/',
  
  /* Global setup for authentication */
  globalSetup: './e2e/global-setup.ts',
  
  /* Global teardown */
  globalTeardown: undefined,
});
