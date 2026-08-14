import { test, expect, type Page } from '@playwright/test';

const provider = process.env.E2E_PROVIDER?.toLowerCase();
const providerEmail = process.env.E2E_PROVIDER_EMAIL;
const providerPassword = process.env.E2E_PROVIDER_PASSWORD;
const enabled = process.env.E2E_PROVIDER_E2E === '1';

async function assertBackendIdentity(page: Page, expectedEmail?: string) {
  const response = await page.request.get('/api/v1/auth/me', {
    headers: { accept: 'application/json' },
  });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  const profile = payload?.data ?? payload?.user ?? payload;
  if (expectedEmail) {
    expect(profile.email).toBe(expectedEmail);
  }
}

test.describe('Real OAuth provider flow', () => {
  test.skip(
    !enabled || !provider || !providerEmail || !providerPassword,
    'Set E2E_PROVIDER_E2E=1, E2E_PROVIDER, and dedicated provider credentials',
  );

  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await page.goto('/auth/login');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test('completes provider login and backend session exchange', async ({ page }) => {
    test.skip(!['github', 'google'].includes(provider ?? ''), 'Unsupported provider');

    const providerButton = page.getByRole('button', {
      name: new RegExp(provider ?? '', 'i'),
    });
    await expect(providerButton).toBeVisible();

    if (provider === 'github') {
      await providerButton.click();
      await page.waitForURL(/github\.com\/(login|login\/oauth\/authorize|oauth\/authorize)/);
      if (page.url().includes('/login')) {
        await page.locator('input[name="login"]').fill(providerEmail ?? '');
        await page.locator('input[name="password"]').fill(providerPassword ?? '');
        await page.getByRole('button', { name: /sign in/i }).click();
      }
      await page.waitForURL(/\/auth\/callback\/github|\/dashboard/);
    } else {
      // @react-oauth/google uses a popup for the implicit flow. Keep the
      // opener as the app page so the token exchange and redirect are tested.
      const popupPromise = page.waitForEvent('popup', { timeout: 15_000 }).catch(() => null);
      await providerButton.click();
      const authPage = (await popupPromise) ?? page;
      await authPage.waitForURL(/accounts\.google\.com/, { timeout: 30_000 });
      await authPage.locator('input[type="email"]').fill(providerEmail ?? '');
      await authPage.getByRole('button', { name: /next/i }).click();
      await authPage.locator('input[type="password"]').fill(providerPassword ?? '');
      await authPage.getByRole('button', { name: /next/i }).click();
      if (authPage !== page) {
        await authPage.waitForEvent('close', { timeout: 30_000 }).catch(() => undefined);
      }
    }

    await expect(page).not.toHaveURL(/\/auth\/login/);
    await assertBackendIdentity(page, process.env.E2E_EXPECTED_PROVIDER_EMAIL);
  });
});
