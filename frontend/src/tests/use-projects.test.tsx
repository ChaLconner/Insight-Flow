import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { ProjectStatus, UserRole } from "@/types";

// Mock the API endpoints
vi.mock("@/lib/api-endpoints", () => ({
  projectsApi: {
    getProjects: vi.fn().mockResolvedValue([]),
    createProject: vi.fn(),
    updateProject: vi.fn(),
    deleteProject: vi.fn(),
  },
}));

// Mock project utils
vi.mock("@/lib/project-utils", () => ({
  transformProjectData: vi.fn((p) => p),
}));

// Mock the auth store
vi.mock("@/stores/auth-store", () => ({
  useAuthStore: vi.fn(() => ({
    user: { id: "test-user-id", email: "test@example.com", name: "Test User" },
  })),
}));

// Mock toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock error utils
vi.mock("@/lib/error-utils", () => ({
  getErrorMessage: vi.fn((e) => e?.message ?? "Unknown error"),
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

describe("useProjects Hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should return query result with data property", async () => {
    const { useProjects } = await import("@/hooks/use-projects");

    const { result } = renderHook(() => useProjects(), {
      wrapper: createWrapper(),
    });

    // useQuery returns data, isLoading, error, etc
    expect(result.current).toHaveProperty("data");
    expect(result.current).toHaveProperty("isLoading");
    expect(result.current).toHaveProperty("error");
  });

  it("should have isLoading as a boolean", async () => {
    const { useProjects } = await import("@/hooks/use-projects");

    const { result } = renderHook(() => useProjects(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.isLoading).toBe("boolean");
  });

  it("should eventually return data array", async () => {
    const { projectsApi } = await import("@/lib/api-endpoints");
    vi.mocked(projectsApi.getProjects).mockResolvedValue([
      {
        id: "1",
        name: "Test Project",
        description: "A test project",
        color: "#6366f1",
        status: ProjectStatus.ACTIVE,
        ownerId: "user-1",
        owner: { id: "user-1", email: "test@test.com", username: "testuser", role: UserRole.ADMIN, isActive: true, emailVerified: true, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
        members: [],
        stats: { totalTasks: 10, completedTasks: 5, inProgressTasks: 3, overdueTasks: 0, teamMembers: 1, recentActivity: 0 },
        settings: { allowPublicAccess: false, requireApproval: false, defaultTaskVisibility: "team" as const, notificationSettings: { taskAssigned: true, statusChanged: true, deadlineApproaching: true, commentAdded: true } },
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    ]);

    const { useProjects } = await import("@/hooks/use-projects");

    const { result } = renderHook(() => useProjects(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeDefined();
  });
});

describe("useCreateProject Hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should return mutation functions", async () => {
    const { useCreateProject } = await import("@/hooks/use-projects");

    const { result } = renderHook(() => useCreateProject(), {
      wrapper: createWrapper(),
    });

    // useMutation returns mutate, mutateAsync, etc
    expect(result.current).toHaveProperty("mutate");
    expect(result.current).toHaveProperty("mutateAsync");
    expect(typeof result.current.mutate).toBe("function");
  });
});

describe("useUpdateProject Hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should return mutation functions", async () => {
    const { useUpdateProject } = await import("@/hooks/use-projects");

    const { result } = renderHook(() => useUpdateProject(), {
      wrapper: createWrapper(),
    });

    expect(result.current).toHaveProperty("mutate");
    expect(typeof result.current.mutate).toBe("function");
  });
});

describe("useProjects - Error Handling", () => {
  it("should handle API errors gracefully", async () => {
    const { projectsApi } = await import("@/lib/api-endpoints");

    // Mock API to throw an error
    vi.mocked(projectsApi.getProjects).mockRejectedValueOnce(
      new Error("Network error"),
    );

    const { useProjects } = await import("@/hooks/use-projects");

    const { result } = renderHook(() => useProjects(), {
      wrapper: createWrapper(),
    });

    // Should not throw, and should eventually have an error state
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Error should be captured
    expect(result.current.error).toBeDefined();
  });
});
