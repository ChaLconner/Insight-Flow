import { afterEach, describe, expect, it, vi } from "vitest";

describe("runtime diagnostics flags", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("disables development diagnostics during E2E runs", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("NEXT_PUBLIC_E2E", "1");

    const { shouldEnableDevelopmentDiagnostics } = await import(
      "@/lib/runtime-flags"
    );
    const { shouldRenderQueryDevtools } = await import(
      "@/providers/query-provider"
    );
    const { shouldEnableWebVitals } = await import(
      "@/components/analytics/web-vitals-reporter"
    );
    const { shouldRunDevelopmentServiceWorkerCleanup } = await import(
      "@/components/providers/service-worker-registration"
    );

    expect(shouldEnableDevelopmentDiagnostics()).toBe(false);
    expect(shouldRenderQueryDevtools()).toBe(false);
    expect(shouldEnableWebVitals()).toBe(false);
    expect(shouldRunDevelopmentServiceWorkerCleanup()).toBe(false);
  });

  it("keeps diagnostics available for normal development", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("NEXT_PUBLIC_E2E", "");

    const { shouldEnableDevelopmentDiagnostics } = await import(
      "@/lib/runtime-flags"
    );
    const { shouldRenderQueryDevtools } = await import(
      "@/providers/query-provider"
    );
    const { shouldEnableWebVitals } = await import(
      "@/components/analytics/web-vitals-reporter"
    );
    const { shouldRunDevelopmentServiceWorkerCleanup } = await import(
      "@/components/providers/service-worker-registration"
    );

    expect(shouldEnableDevelopmentDiagnostics()).toBe(true);
    expect(shouldRenderQueryDevtools()).toBe(true);
    expect(shouldEnableWebVitals()).toBe(true);
    expect(shouldRunDevelopmentServiceWorkerCleanup()).toBe(true);
  });
});

