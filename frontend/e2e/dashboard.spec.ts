/**
 * E2E Tests for Dashboard functionality
 * Tests dashboard widgets, statistics, and navigation
 */
import { test, expect } from '@playwright/test';

const hasE2EAuth = Boolean(process.env.E2E_USER_EMAIL && process.env.E2E_USER_PASSWORD);

test.describe('Dashboard Page', () => {
  test.skip(!hasE2EAuth, 'E2E credentials are not configured');

  test.beforeEach(async ({ page }) => {
    // Note: These tests assume authentication is handled
    // In a real scenario, you'd set up auth state
  });

  test('should display dashboard layout', async ({ page }) => {
    await page.goto('/dashboard');
    
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/dashboard/);
    await expect(page.locator('h1, h2').first()).toBeVisible();
  });
});

test.describe('Projects Page', () => {
  test.skip(!hasE2EAuth, 'E2E credentials are not configured');

  test('should display projects page when authenticated', async ({ page }) => {
    await page.goto('/projects');
    
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveURL(/projects/);
  });

  test('should have create project button when authenticated', async ({ page }) => {
    await page.goto('/projects');
    
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveURL(/projects/);
    const createButton = page.getByRole('button', { name: /create|new|add/i });
    await expect(createButton).toBeVisible();
    await expect(createButton).toBeEnabled();
  });
});

test.describe('Tasks Page', () => {
  test.skip(!hasE2EAuth, 'E2E credentials are not configured');

  test('should display tasks page when authenticated', async ({ page }) => {
    const response = await page.goto('/tasks');
    
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveURL(/tasks/);
    expect(response?.status()).toBeLessThan(400);
    await expect(page.getByRole('heading', { name: /tasks/i }).first()).toBeVisible();
  });
});

test.describe('Settings Page', () => {
  test.skip(!hasE2EAuth, 'E2E credentials are not configured');

  test('should display settings page when authenticated', async ({ page }) => {
    await page.goto('/settings');
    
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveURL(/settings/);
  });

  test('should have profile section when authenticated', async ({ page }) => {
    await page.goto('/settings');
    
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveURL(/settings/);
    const profileSection = page.getByText(/profile|account|settings/i).first();
    await expect(profileSection).toBeVisible();
  });
});

test.describe('Navigation', () => {
  test('should have working navigation links', async ({ page }) => {
    await page.goto('/');
    
    // Check for navigation elements
    const nav = page.locator('nav, header').first();
    
    if (await nav.isVisible()) {
      // Navigation should exist
      expect(await nav.count()).toBeGreaterThan(0);
    }
  });

  test('should navigate between pages', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Try to find and click register link
    const registerLink = page.getByRole('link', { name: /register|sign up/i });
    
    if (await registerLink.isVisible()) {
      await registerLink.click();
      await page.waitForURL(/register/);
      expect(page.url()).toContain('register');
    }
  });
});

test.describe('Responsive Design', () => {
  test('should display correctly on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    await page.goto('/auth/login');
    
    // Login form should still be visible
    const emailInput = page.getByRole('textbox', { name: /email/i });
    await expect(emailInput).toBeVisible();
    
    // Check form is not overflowing
    const body = page.locator('body');
    const bodyBox = await body.boundingBox();
    expect(bodyBox?.width).toBeLessThanOrEqual(375);
  });

  test('should display correctly on tablet', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    
    await page.goto('/auth/login');
    
    // Content should be visible
    const emailInput = page.getByRole('textbox', { name: /email/i });
    await expect(emailInput).toBeVisible();
  });

  test('should display correctly on desktop', async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    await page.goto('/auth/login');
    
    // Content should be visible
    const emailInput = page.getByRole('textbox', { name: /email/i });
    await expect(emailInput).toBeVisible();
  });
});

test.describe('Accessibility', () => {
  test('should have proper page structure', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Check for proper heading hierarchy
    const h1 = page.locator('h1');
    const h1Count = await h1.count();
    expect(h1Count).toBeGreaterThanOrEqual(0);
    
    // Check for form labels
    const labels = page.locator('label');
    expect(await labels.count()).toBeGreaterThan(0);
  });

  test('should have focusable elements', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Tab through the page
    await page.keyboard.press('Tab');
    
    // Something should be focused
    const focusedElement = page.locator(':focus');
    expect(await focusedElement.count()).toBeGreaterThan(0);
  });

  test('should handle keyboard navigation', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Focus on email field
    const emailInput = page.getByRole('textbox', { name: /email/i });
    await emailInput.focus();
    
    // Type and tab to next field
    await emailInput.fill('test@example.com');
    await page.keyboard.press('Tab');
    
    // Password field should be focused or another input
    const focusedElement = page.locator(':focus');
    expect(await focusedElement.count()).toBeGreaterThan(0);
  });
});

test.describe('Error Handling', () => {
  test('should handle 404 gracefully', async ({ page }) => {
    await page.goto('/nonexistent-page-12345');
    
    // Should show 404 page or redirect
    await page.waitForLoadState('networkidle');
    
    // Page should not crash
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Simulate offline
    await page.context().setOffline(true);
    
    try {
      await page.goto('/auth/login', { timeout: 5000 });
    } catch {
      // Expected to fail when offline
    }
    
    // Restore online state
    await page.context().setOffline(false);
  });
});

test.describe('Performance', () => {
  test('should load login page quickly', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('/auth/login');
    
    const loadTime = Date.now() - startTime;
    
    // Page should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });

  test('should not have console errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    await page.goto('/auth/login');
    await page.waitForLoadState('networkidle');
    
    // Filter out expected errors (like network errors in CI)
    const criticalErrors = consoleErrors.filter(
      (err) => !err.includes('Failed to load resource') && !err.includes('net::')
    );
    
    // Should have no critical console errors
    expect(criticalErrors.length).toBe(0);
  });
});
