import type { Page } from "@playwright/test";

/**
 * Start a test with no authenticated browser state while keeping the
 * project's browser-specific authenticated state available to protected tests.
 *
 * The init script runs once for the page's first document. The marker survives
 * same-page navigations, so tests that log in after the reset keep that session.
 */
export async function resetAuthState(page: Page): Promise<void> {
  await page.context().clearCookies();
  await page.addInitScript(() => {
    const marker = "__playwright_auth_state_cleared__";
    if (window.sessionStorage.getItem(marker) === "1") {
      return;
    }

    window.localStorage.clear();
    window.sessionStorage.clear();
    window.sessionStorage.setItem(marker, "1");
  });
}
