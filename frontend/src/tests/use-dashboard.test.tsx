import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { ProjectStatus, UserRole } from "@/types";

// Mock the API endpoints
vi.mock("@/lib/api-endpoints", () => ({
  dashboardApi: {
    getOverview: vi.fn().mockResolvedValue({
      stats: {
        totalProjects: 5,
        totalTasks: 20,
        completedTasks: 10,
        pendingTasks: 5,
        teamMembers: 3,
        inProgressTasks: 5,
        pendingReviewTasks: 3,
        teamVelocity: 85,
      },
      recentProjects: [],
      recentActivities: [],
      upcomingDeadlines: [],
      charts: [],
    }),
  },
}));

// Create a wrapper for React Query
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

describe("useDashboard Hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should return query result with expected properties", async () => {
    const { useDashboard } = await import("@/hooks/use-dashboard");

    const { result } = renderHook(() => useDashboard(), {
      wrapper: createWrapper(),
    });

    // Should have React Query result properties
    expect(result.current).toHaveProperty("data");
    expect(result.current).toHaveProperty("isLoading");
    expect(result.current).toHaveProperty("error");
  });

  it("should have isLoading as a boolean", async () => {
    const { useDashboard } = await import("@/hooks/use-dashboard");

    const { result } = renderHook(() => useDashboard(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.isLoading).toBe("boolean");
  });

  it("should not fetch dashboard data when disabled", async () => {
    const { dashboardApi } = await import("@/lib/api-endpoints");
    const { useDashboard } = await import("@/hooks/use-dashboard");

    renderHook(() => useDashboard({ enabled: false }), {
      wrapper: createWrapper(),
    });

    expect(dashboardApi.getOverview).not.toHaveBeenCalled();
  });

  it("should transform API response with select function", async () => {
    const { dashboardApi } = await import("@/lib/api-endpoints");

    vi.mocked(dashboardApi.getOverview).mockResolvedValue({
      stats: {
        totalProjects: 3,
        totalTasks: 15,
        completedTasks: 5,
        pendingTasks: 3,
        teamMembers: 2,
        inProgressTasks: 7,
        pendingReviewTasks: 2,
        teamVelocity: 90,
      },
      recentProjects: [
        {
          id: "1",
          name: "Project 1",
          description: "Test project",
          color: "#6366f1",
          status: ProjectStatus.ACTIVE,
          ownerId: "user-1",
          owner: { id: "user-1", email: "test@test.com", username: "testuser", role: UserRole.ADMIN, isActive: true, emailVerified: true, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
          members: [],
          stats: { totalTasks: 10, completedTasks: 5, inProgressTasks: 3, overdueTasks: 0, teamMembers: 1, recentActivity: 0 },
          settings: { allowPublicAccess: false, requireApproval: false, defaultTaskVisibility: "team" as const, notificationSettings: { taskAssigned: true, statusChanged: true, deadlineApproaching: true, commentAdded: true } },
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          progress: 50,
        },
      ],
      recentActivities: [],
      upcomingDeadlines: [],
      charts: [],
    });

    const { useDashboard } = await import("@/hooks/use-dashboard");

    const { result } = renderHook(() => useDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Data should be defined after loading
    expect(result.current.data).toBeDefined();
  });

  it("should handle missing stats with default values", async () => {
      const { dashboardApi } = await import("@/lib/api-endpoints");
      // Mock with minimal/empty stats to trigger null coalescing
      vi.mocked(dashboardApi.getOverview).mockResolvedValue({
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          stats: {} as any, 
          recentProjects: [],
          recentActivities: [],
          upcomingDeadlines: [],
          charts: [],
      });

      const { useDashboard } = await import("@/hooks/use-dashboard");
      const { result } = renderHook(() => useDashboard(), {
          wrapper: createWrapper(),
      });

      await waitFor(() => {
          expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data?.stats.totalProjects).toBe(0);
      expect(result.current.data?.stats.totalTasks).toBe(0);
      expect(result.current.data?.stats.completedTasks).toBe(0);
      expect(result.current.data?.stats.pendingReviewTasks).toBe(0);
      expect(result.current.data?.stats.teamVelocity).toBe(0);
      // Ensure it doesn't crash
      expect(result.current.data?.recentProjects).toEqual([]);
  });
});

describe("useDashboard - Data Structure", () => {
  it("should return data with stats, recentProjects, and recentActivities", async () => {
    const { dashboardApi } = await import("@/lib/api-endpoints");

    vi.mocked(dashboardApi.getOverview).mockResolvedValue({
      stats: {
        totalProjects: 2,
        totalTasks: 10,
        completedTasks: 3,
        pendingTasks: 2,
        teamMembers: 1,
        inProgressTasks: 4,
        pendingReviewTasks: 1,
        teamVelocity: 75,
      },
      recentProjects: [
        {
          id: "1",
          name: "Test",
          description: "Test project",
          color: "#6366f1",
          status: ProjectStatus.ACTIVE,
          ownerId: "user-1",
          owner: { id: "user-1", email: "test@test.com", username: "testuser", role: UserRole.ADMIN, isActive: true, emailVerified: true, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
          members: [],
          stats: { totalTasks: 5, completedTasks: 2, inProgressTasks: 2, overdueTasks: 0, teamMembers: 1, recentActivity: 0 },
          settings: { allowPublicAccess: false, requireApproval: false, defaultTaskVisibility: "team" as const, notificationSettings: { taskAssigned: true, statusChanged: true, deadlineApproaching: true, commentAdded: true } },
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          progress: 25,
        },
      ],
      recentActivities: [],
      upcomingDeadlines: [],
      charts: [],
    });

    const { useDashboard } = await import("@/hooks/use-dashboard");

    const { result } = renderHook(() => useDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    if (result.current.data) {
      expect(result.current.data).toHaveProperty("stats");
      expect(result.current.data).toHaveProperty("recentProjects");
      expect(result.current.data).toHaveProperty("recentActivities");
    }
  });
});

describe("useDashboard - Error Handling", () => {
  it("should handle API errors gracefully", async () => {
    const { dashboardApi } = await import("@/lib/api-endpoints");

    // Mock API to throw an error
    vi.mocked(dashboardApi.getOverview).mockRejectedValueOnce(
      new Error("Dashboard API error"),
    );

    const { useDashboard } = await import("@/hooks/use-dashboard");

    const { result } = renderHook(() => useDashboard(), {
      wrapper: createWrapper(),
    });

    // Should not throw and should have error handling
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Error should be captured
    expect(result.current.error).toBeDefined();
  });
});

describe("useDashboard - Query Keys", () => {
  it("should export query key factory", async () => {
    const { dashboardKeys } = await import("@/hooks/use-dashboard");

    expect(dashboardKeys).toBeDefined();
    expect(dashboardKeys.all).toEqual(["dashboard"]);
    expect(dashboardKeys.overview()).toEqual(["dashboard", "overview"]);
  });
});
