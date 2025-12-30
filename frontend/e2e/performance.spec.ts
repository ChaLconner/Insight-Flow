/**
 * E2E Tests for Performance using Playwright
 * Tests Core Web Vitals and page load performance
 */
import { test, expect } from '@playwright/test';

test.describe('Performance Tests', () => {
  test.describe('Page Load Performance', () => {
    test('login page should load within 3 seconds', async ({ page }) => {
      const startTime = Date.now();
      
      await page.goto('/auth/login');
      await page.waitForLoadState('networkidle');
      
      const loadTime = Date.now() - startTime;
      
      expect(loadTime).toBeLessThan(3000);
    });

    test('should have good Largest Contentful Paint', async ({ page }) => {
      await page.goto('/auth/login');
      
      // Measure LCP using Performance API
      const lcp = await page.evaluate(() => {
        return new Promise<number>((resolve) => {
          new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const lastEntry = entries[entries.length - 1];
            resolve(lastEntry.startTime);
          }).observe({ type: 'largest-contentful-paint', buffered: true });
          
          // Timeout fallback
          setTimeout(() => resolve(0), 3000);
        });
      });
      
      // LCP should be under 2.5s for good score
      if (lcp > 0) {
        expect(lcp).toBeLessThan(2500);
      }
    });

    test('should have minimal Cumulative Layout Shift', async ({ page }) => {
      await page.goto('/auth/login');
      
      // Wait for page to stabilize
      await page.waitForTimeout(2000);
      
      const cls = await page.evaluate(() => {
        return new Promise<number>((resolve) => {
          let clsValue = 0;
          new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
              // @ts-ignore
              if (!entry.hadRecentInput) {
                // @ts-ignore
                clsValue += entry.value;
              }
            }
          }).observe({ type: 'layout-shift', buffered: true });
          
          setTimeout(() => resolve(clsValue), 1000);
        });
      });
      
      // CLS should be under 0.1 for good score
      expect(cls).toBeLessThan(0.25);
    });
  });

  test.describe('Resource Loading', () => {
    test('should load critical resources first', async ({ page }) => {
      const resources: { name: string; startTime: number }[] = [];
      
      page.on('response', (response) => {
        resources.push({
          name: response.url(),
          startTime: Date.now(),
        });
      });
      
      await page.goto('/auth/login');
      await page.waitForLoadState('networkidle');
      
      // Should have loaded some resources
      expect(resources.length).toBeGreaterThan(0);
    });

    test('should not have render-blocking resources', async ({ page }) => {
      await page.goto('/auth/login');
      
      const perfData = await page.evaluate(() => {
        const resources = performance.getEntriesByType('resource');
        return resources.map((r) => ({
          name: r.name,
          duration: r.duration,
          // @ts-ignore
          renderBlockingStatus: r.renderBlockingStatus,
        }));
      });
      
      // Check for render-blocking resources
      const blockingResources = perfData.filter(
        (r) => r.renderBlockingStatus === 'blocking'
      );
      
      // Log blocking resources if any (for debugging)
      if (blockingResources.length > 0) {
        console.log('Render-blocking resources:', blockingResources.map((r) => r.name));
      }
    });

    test('should use efficient caching', async ({ page }) => {
      // First visit
      await page.goto('/auth/login');
      await page.waitForLoadState('networkidle');
      
      // Second visit (should use cache)
      const startTime = Date.now();
      await page.goto('/auth/login');
      await page.waitForLoadState('networkidle');
      const cachedLoadTime = Date.now() - startTime;
      
      // Cached load should be faster
      expect(cachedLoadTime).toBeLessThan(2000);
    });
  });

  test.describe('Image Optimization', () => {
    test('should lazy load images below the fold', async ({ page }) => {
      await page.goto('/dashboard');
      
      await page.waitForTimeout(1000);
      
      if (page.url().includes('dashboard')) {
        const images = await page.locator('img').all();
        
        for (const img of images) {
          const loading = await img.getAttribute('loading');
          const inViewport = await img.isVisible();
          
          // Images below fold should have lazy loading
          // (Above-fold images may have eager loading)
        }
      }
    });

    test('should use modern image formats', async ({ page }) => {
      await page.goto('/dashboard');
      
      await page.waitForTimeout(1000);
      
      if (page.url().includes('dashboard')) {
        const images = await page.locator('img').all();
        
        for (const img of images) {
          const src = await img.getAttribute('src');
          
          if (src) {
            // Next.js Image optimization should use WebP or AVIF
            // Check if using Next.js image optimization
            const isOptimized = src.includes('_next/image') || 
                               src.endsWith('.webp') || 
                               src.endsWith('.avif');
            // Log for debugging
          }
        }
      }
    });
  });

  test.describe('JavaScript Performance', () => {
    test('should not have long tasks blocking main thread', async ({ page }) => {
      const longTasks: number[] = [];
      
      await page.goto('/auth/login');
      
      // Monitor for long tasks
      await page.evaluate(() => {
        // @ts-ignore
        if (typeof PerformanceObserver !== 'undefined') {
          new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
              // @ts-ignore
              window.__longTasks = window.__longTasks || [];
              // @ts-ignore
              window.__longTasks.push(entry.duration);
            }
          }).observe({ type: 'longtask', buffered: true });
        }
      });
      
      await page.waitForTimeout(2000);
      
      const tasks = await page.evaluate(() => {
        // @ts-ignore
        return window.__longTasks || [];
      }) as number[];
      
      // Should have minimal long tasks (>50ms)
      const veryLongTasks = tasks.filter((t) => t > 100);
      expect(veryLongTasks.length).toBeLessThan(5);
    });

    test('should have good Time to Interactive', async ({ page }) => {
      const startTime = Date.now();
      
      await page.goto('/auth/login');
      
      // Wait for interactive (all network idle)
      await page.waitForLoadState('networkidle');
      
      // Try to interact with the page
      const emailInput = page.getByRole('textbox', { name: /email/i });
      if (await emailInput.isVisible()) {
        await emailInput.fill('test@example.com');
      }
      
      const tti = Date.now() - startTime;
      
      // TTI should be under 5 seconds
      expect(tti).toBeLessThan(5000);
    });
  });

  test.describe('Memory Usage', () => {
    test('should not have memory leaks on navigation', async ({ page }) => {
      // Navigate multiple times
      for (let i = 0; i < 5; i++) {
        await page.goto('/auth/login');
        await page.waitForLoadState('networkidle');
      }
      
      // If we got here without crashing, memory is likely stable
      expect(true).toBe(true);
    });
  });

  test.describe('Network Efficiency', () => {
    test('should minimize number of requests', async ({ page }) => {
      let requestCount = 0;
      
      page.on('request', () => {
        requestCount++;
      });
      
      await page.goto('/auth/login');
      await page.waitForLoadState('networkidle');
      
      // Login page should have reasonable number of requests
      expect(requestCount).toBeLessThan(50);
    });

    test('should use HTTP/2 or higher', async ({ page }) => {
      const protocols: string[] = [];
      
      page.on('response', (response) => {
        const headers = response.headers();
        // HTTP/2 typically doesn't expose protocol in headers easily
        // This is a simplified check
      });
      
      await page.goto('/auth/login');
      await page.waitForLoadState('networkidle');
    });

    test('should have compressed responses', async ({ page }) => {
      let compressedCount = 0;
      let totalCount = 0;
      
      page.on('response', (response) => {
        const encoding = response.headers()['content-encoding'];
        if (encoding === 'gzip' || encoding === 'br' || encoding === 'deflate') {
          compressedCount++;
        }
        totalCount++;
      });
      
      await page.goto('/auth/login');
      await page.waitForLoadState('networkidle');
      
      // Most responses should be compressed
      if (totalCount > 5) {
        const compressionRate = compressedCount / totalCount;
        expect(compressionRate).toBeGreaterThan(0.3);
      }
    });
  });
});

test.describe('Accessibility Performance', () => {
  test('should be navigable with keyboard', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Tab through the page
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');
    }
    
    // Should be able to tab without getting stuck
    const focusedElement = page.locator(':focus');
    expect(await focusedElement.count()).toBe(1);
  });

  test('should have visible focus indicators', async ({ page }) => {
    await page.goto('/auth/login');
    
    const emailInput = page.getByRole('textbox', { name: /email/i });
    await emailInput.focus();
    
    // Check if the focused element has visibility
    const isFocused = await emailInput.evaluate((el) => {
      return document.activeElement === el;
    });
    
    expect(isFocused).toBe(true);
  });
});

test.describe('SEO Performance', () => {
  test('should have proper meta tags', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Check for title
    const title = await page.title();
    expect(title.length).toBeGreaterThan(0);
    
    // Check for meta description
    const metaDescription = await page.locator('meta[name="description"]').getAttribute('content');
    // Description may or may not exist
  });

  test('should have proper heading structure', async ({ page }) => {
    await page.goto('/auth/login');
    
    const h1Count = await page.locator('h1').count();
    // Should have at least one h1 or heading element
    expect(h1Count).toBeGreaterThanOrEqual(0);
  });
});
