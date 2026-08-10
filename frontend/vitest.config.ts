import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/tests/setup.ts",
    exclude: ["node_modules", "e2e/**", "playwright.config.ts"],
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    // Keep the client-side quality gate above the minimum branch threshold.
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html", "lcov"],
      reportsDirectory: "./coverage",
      exclude: [
        "node_modules/**",
        "e2e/**",
        "**/*.d.ts",
        "**/*.config.*",
        "**/types/**",
        "**/__mocks__/**",
        "**/tests/setup.ts",
        "**/components/providers/service-worker-registration.tsx",
        "**/components/analytics/web-vitals-reporter.tsx",
      ],
      thresholds: {
        statements: 80,
        branches: 65,
        functions: 75,
        lines: 80,
      },
    },
    // Performance optimizations
    pool: "threads",
    reporters: ["verbose"],
    // Watch mode optimizations
    watch: false,
    // Timeout settings
    testTimeout: 10000,
    hookTimeout: 10000,
  },
});
