import { test, expect, type Page } from '@playwright/test';
import { getPostLoginRedirect } from '../src/lib/auth-redirect';

const userA = {
  email: process.env.E2E_USER_A_EMAIL,
  password: process.env.E2E_USER_A_PASSWORD,
  role: process.env.E2E_USER_A_ROLE ?? 'manager',
  marker: process.env.E2E_USER_A_PROJECT_MARKER,
};
const userB = {
  email: process.env.E2E_USER_B_EMAIL,
  password: process.env.E2E_USER_B_PASSWORD,
  role: process.env.E2E_USER_B_ROLE ?? 'manager',
  marker: process.env.E2E_USER_B_PROJECT_MARKER,
};
const hasTwoUsers = Boolean(
  userA.email && userA.password && userB.email && userB.password,
);

async function login(page: Page, user: typeof userA) {
  await page.goto('/auth/login');
  await page.getByRole('textbox', { name: /email/i }).fill(user.email ?? '');
  await page.locator('input[type="password"]').fill(user.password ?? '');
  await page.getByRole('button', { name: /sign in|login/i }).click();

  const expectedPath = getPostLoginRedirect(user.role);
  await page.waitForURL((url) => url.pathname === new URL(expectedPath, page.url()).pathname);
}

async function getJson(page: Page, path: string) {
  const response = await page.request.get(path, {
    headers: { accept: 'application/json' },
  });
  expect(response.ok()).toBeTruthy();
  return response.json();
}

function unwrapProfile(payload: unknown): Record<string, unknown> {
  if (payload && typeof payload === 'object') {
    const record = payload as Record<string, unknown>;
    if (record.data && typeof record.data === 'object') {
      return record.data as Record<string, unknown>;
    }
    if (record.user && typeof record.user === 'object') {
      return record.user as Record<string, unknown>;
    }
    return record;
  }
  return {};
}

function projectNames(payload: unknown): string[] {
  const projects = Array.isArray(payload)
    ? payload
    : payload && typeof payload === 'object' && Array.isArray((payload as Record<string, unknown>).data)
      ? (payload as Record<string, unknown>).data
      : [];
  return projects.flatMap((project) => {
    if (!project || typeof project !== 'object') return [];
    const name = (project as Record<string, unknown>).name;
    return typeof name === 'string' ? [name] : [];
  });
}

test.describe('Two-user account switching and API isolation', () => {
  test.skip(
    !hasTwoUsers,
    'E2E_USER_A_* and E2E_USER_B_* credentials are required for account-isolation E2E',
  );

  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await page.goto('/auth/login');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test('switches identity without reusing the previous account response', async ({ page }) => {
    await login(page, userA);
    const profileA = unwrapProfile(await getJson(page, '/api/v1/auth/me'));
    const projectsA = projectNames(await getJson(page, '/api/v1/projects'));
    expect(profileA.email).toBe(userA.email);

    // Clear cookies only. This preserves the current document's in-memory
    // caches and exercises the same account-transition boundary directly.
    await page.context().clearCookies();
    await login(page, userB);
    const profileB = unwrapProfile(await getJson(page, '/api/v1/auth/me'));
    const projectsB = projectNames(await getJson(page, '/api/v1/projects'));
    expect(profileB.email).toBe(userB.email);
    expect(profileB.email).not.toBe(profileA.email);

    if (userA.marker && userB.marker) {
      expect(projectsA).toContain(userA.marker);
      expect(projectsA).not.toContain(userB.marker);
      expect(projectsB).toContain(userB.marker);
      expect(projectsB).not.toContain(userA.marker);
    }
  });
});
