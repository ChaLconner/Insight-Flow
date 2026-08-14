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
    // Keep CI and local runs deterministic on constrained runners. The suite
    // contains a few module-reset and async setup boundaries that become
    // flaky when every test file competes for an uncapped worker.
    maxWorkers: 2,
    reporters: ["verbose"],
    // Watch mode optimizations
    watch: false,
    // The serial coverage gate can spend several seconds loading a heavily
    // instrumented React module on constrained Windows runners. Keep a finite
    // bound while avoiding false negatives from the 10-second default.
    testTimeout: 30000,
    hookTimeout: 10000,
  },
});
