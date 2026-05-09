import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
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
    const { useAnalytics } = await import("@/hooks/use-analytics");

    renderHook(
      () => useAnalytics(AnalyticsPeriod.MONTH, { enabled: false }),
      { wrapper: createWrapper() },
    );

    expect(analyticsApi.getAnalytics).not.toHaveBeenCalled();
  });
});
