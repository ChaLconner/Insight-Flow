import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useAnalytics, useTeamWorkload } from "@/hooks/use-analytics";
import { AnalyticsPeriod } from "@/types";

vi.mock("@/lib/api-endpoints", () => ({
  analyticsApi: {
    getAnalytics: vi.fn().mockResolvedValue({
      overview: {},
      trends: [],
      projects: [],
      teamWorkload: [],
      statusDistribution: [],
      priorityDistribution: [],
      totalTasks: 10,
    }),
    getTeamWorkload: vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      pageSize: 10,
      totalPages: 0,
    }),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useAnalytics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should not fetch analytics data when disabled", async () => {
    const { analyticsApi } = await import("@/lib/api-endpoints");

    renderHook(
      () => useAnalytics(AnalyticsPeriod.MONTH, { enabled: false }),
      { wrapper: createWrapper() },
    );

    expect(analyticsApi.getAnalytics).not.toHaveBeenCalled();
  });

  it("fetches analytics with enabled true and false", () => {
    const { result: resEnabled } = renderHook(
      () => useAnalytics(AnalyticsPeriod.WEEK, { enabled: true }),
      { wrapper: createWrapper() },
    );
    expect(resEnabled.current).toBeDefined();

    const { result: resDisabled } = renderHook(
      () => useAnalytics(AnalyticsPeriod.WEEK, { enabled: false }),
      { wrapper: createWrapper() },
    );
    expect(resDisabled.current.isPending).toBe(true);
  });

  it("fetches team workload with options", () => {
    const { result } = renderHook(
      () => useTeamWorkload({ page: 1 }, { enabled: true }),
      { wrapper: createWrapper() },
    );
    expect(result.current).toBeDefined();
  });
});
