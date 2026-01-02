import { test, expect, Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * Visual Regression & Accessibility Tests - Staff/Principal Level
 *
 * Provides:
 * - Visual regression testing with screenshot comparison
 * - Accessibility testing with axe-core
 * - Responsive design verification
 * - Dark mode visual testing
 */

// =============================================================================
// Visual Regression Tests
// =============================================================================

test.describe("Visual Regression Tests", () => {
  test.describe("Dashboard", () => {
    test("dashboard visual regression - light mode", async ({ page }) => {
      await page.goto("/dashboard");
      await page.waitForLoadState("networkidle");

      // Wait for dynamic content to load
      await page.waitForTimeout(1000);

      // Take screenshot and compare
      await expect(page).toHaveScreenshot("dashboard-light.png", {
        maxDiffPixelRatio: 0.01, // 1% tolerance
        animations: "disabled",
        mask: [
          // Mask dynamic content that changes between runs
          page.locator('[data-testid="current-time"]'),
          page.locator('[data-testid="user-avatar"]'),
        ],
      });
    });

    test("dashboard visual regression - dark mode", async ({ page }) => {
      // Set dark mode
      await page.emulateMedia({ colorScheme: "dark" });
      await page.goto("/dashboard");
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(1000);

      await expect(page).toHaveScreenshot("dashboard-dark.png", {
        maxDiffPixelRatio: 0.01,
        animations: "disabled",
      });
    });

    test("dashboard responsive - mobile", async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE
      await page.goto("/dashboard");
      await page.waitForLoadState("networkidle");

      await expect(page).toHaveScreenshot("dashboard-mobile.png", {
        maxDiffPixelRatio: 0.02,
        animations: "disabled",
      });
    });

    test("dashboard responsive - tablet", async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 }); // iPad
      await page.goto("/dashboard");
      await page.waitForLoadState("networkidle");

      await expect(page).toHaveScreenshot("dashboard-tablet.png", {
        maxDiffPixelRatio: 0.02,
        animations: "disabled",
      });
    });
  });

  test.describe("Authentication Pages", () => {
    test("login page visual regression", async ({ page }) => {
      await page.goto("/auth/login");
      await page.waitForLoadState("networkidle");

      await expect(page).toHaveScreenshot("login-page.png", {
        maxDiffPixelRatio: 0.01,
        animations: "disabled",
      });
    });

    test("register page visual regression", async ({ page }) => {
      await page.goto("/auth/register");
      await page.waitForLoadState("networkidle");

      await expect(page).toHaveScreenshot("register-page.png", {
        maxDiffPixelRatio: 0.01,
        animations: "disabled",
      });
    });
  });
});

// =============================================================================
// Accessibility Tests (WCAG 2.1 AA Compliance)
// =============================================================================

test.describe("Accessibility Tests", () => {
  const testPages = [
    { name: "Login", path: "/auth/login" },
    { name: "Register", path: "/auth/register" },
    { name: "Dashboard", path: "/dashboard", requiresAuth: true },
    { name: "Projects", path: "/projects", requiresAuth: true },
    { name: "Settings", path: "/settings", requiresAuth: true },
  ];

  // Helper function to run accessibility scan
  async function runAccessibilityScan(
    page: Page,
    options?: {
      skipRules?: string[];
      onlyRules?: string[];
    }
  ) {
    let builder = new AxeBuilder({ page }).withTags([
      "wcag2a",
      "wcag2aa",
      "wcag21a",
      "wcag21aa",
    ]);

    if (options?.skipRules) {
      builder = builder.disableRules(options.skipRules);
    }

    if (options?.onlyRules) {
      builder = builder.withRules(options.onlyRules);
    }

    const results = await builder.analyze();

    return results;
  }

  test.describe("Public Pages", () => {
    for (const { name, path, requiresAuth } of testPages.filter(
      (p) => !p.requiresAuth
    )) {
      test(`${name} page should not have accessibility violations`, async ({
        page,
      }) => {
        await page.goto(path);
        await page.waitForLoadState("networkidle");

        const accessibilityResults = await runAccessibilityScan(page);

        // Log detailed violations for debugging
        if (accessibilityResults.violations.length > 0) {
          console.log(`Accessibility violations on ${name}:`);
          accessibilityResults.violations.forEach((violation) => {
            console.log(`  - ${violation.id}: ${violation.description}`);
            console.log(`    Impact: ${violation.impact}`);
            console.log(`    Nodes: ${violation.nodes.length}`);
          });
        }

        // Assert no critical or serious violations
        const criticalViolations = accessibilityResults.violations.filter(
          (v) => v.impact === "critical" || v.impact === "serious"
        );

        expect(
          criticalViolations,
          `Found ${criticalViolations.length} critical/serious accessibility violations`
        ).toHaveLength(0);
      });
    }
  });

  test.describe("Keyboard Navigation", () => {
    test("login form should be navigable with keyboard", async ({ page }) => {
      await page.goto("/auth/login");
      await page.waitForLoadState("networkidle");

      // Email should be auto-focused or first tab target
      const emailInput = page.locator('input[type="email"]');
      await expect(emailInput).toBeFocused();

      // Tab to password
      await page.keyboard.press("Tab");
      const passwordInput = page.locator('input[type="password"]');
      await expect(passwordInput).toBeFocused();

      // Tab to show password button
      await page.keyboard.press("Tab");
      const showPasswordBtn = page.locator('button[title*="password"]');
      await expect(showPasswordBtn).toBeFocused();
    });

    test("dropdown menus should be keyboard accessible", async ({ page }) => {
      await page.goto("/dashboard");
      await page.waitForLoadState("networkidle");

      // Find a dropdown trigger
      const dropdownTrigger = page.locator('[role="button"][aria-haspopup]').first();
      
      if (await dropdownTrigger.isVisible()) {
        await dropdownTrigger.focus();
        await page.keyboard.press("Enter");

        // Check dropdown opened
        const dropdown = page.locator('[role="menu"]').first();
        await expect(dropdown).toBeVisible();

        // Navigate with arrow keys
        await page.keyboard.press("ArrowDown");
        await page.keyboard.press("Escape");

        // Check dropdown closed
        await expect(dropdown).not.toBeVisible();
      }
    });
  });

  test.describe("Color Contrast", () => {
    test("text should have sufficient color contrast", async ({ page }) => {
      await page.goto("/auth/login");
      await page.waitForLoadState("networkidle");

      const results = await runAccessibilityScan(page, {
        onlyRules: ["color-contrast"],
      });

      expect(
        results.violations.filter((v) => v.id === "color-contrast").length,
        "Color contrast violations found"
      ).toBe(0);
    });

    test("dark mode should maintain color contrast", async ({ page }) => {
      await page.emulateMedia({ colorScheme: "dark" });
      await page.goto("/auth/login");
      await page.waitForLoadState("networkidle");

      const results = await runAccessibilityScan(page, {
        onlyRules: ["color-contrast"],
      });

      expect(
        results.violations.filter((v) => v.id === "color-contrast").length,
        "Dark mode color contrast violations found"
      ).toBe(0);
    });
  });

  test.describe("ARIA and Semantic HTML", () => {
    test("interactive elements should have accessible names", async ({
      page,
    }) => {
      await page.goto("/auth/login");
      await page.waitForLoadState("networkidle");

      const results = await runAccessibilityScan(page, {
        onlyRules: ["button-name", "link-name", "label"],
      });

      expect(
        results.violations.length,
        `Found ${results.violations.length} naming violations`
      ).toBe(0);
    });

    test("form inputs should have associated labels", async ({ page }) => {
      await page.goto("/auth/register");
      await page.waitForLoadState("networkidle");

      const results = await runAccessibilityScan(page, {
        onlyRules: ["label"],
      });

      expect(
        results.violations.length,
        "Form inputs missing labels"
      ).toBe(0);
    });

    test("images should have alt text", async ({ page }) => {
      await page.goto("/dashboard");
      await page.waitForLoadState("networkidle");

      const results = await runAccessibilityScan(page, {
        onlyRules: ["image-alt"],
      });

      expect(
        results.violations.length,
        "Images missing alt text"
      ).toBe(0);
    });
  });
});

// =============================================================================
// Component Visual Tests
// =============================================================================

test.describe("Component Visual Tests", () => {
  test("button states", async ({ page }) => {
    await page.goto("/auth/login");
    await page.waitForLoadState("networkidle");

    const submitButton = page.locator('button[type="submit"]');

    // Normal state
    await expect(submitButton).toHaveScreenshot("button-normal.png");

    // Hover state
    await submitButton.hover();
    await expect(submitButton).toHaveScreenshot("button-hover.png");

    // Focus state
    await submitButton.focus();
    await expect(submitButton).toHaveScreenshot("button-focus.png");
  });

  test("input states", async ({ page }) => {
    await page.goto("/auth/login");
    await page.waitForLoadState("networkidle");

    const emailInput = page.locator('input[type="email"], input[name="email"]').first();

    // Empty state
    await expect(emailInput).toHaveScreenshot("input-empty.png");

    // Focus state
    await emailInput.focus();
    await expect(emailInput).toHaveScreenshot("input-focus.png");

    // Filled state
    await emailInput.fill("test@example.com");
    await expect(emailInput).toHaveScreenshot("input-filled.png");
  });
});
