import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { ProjectStatus, UserRole, type Project } from "@/types";

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

    expect(result.current).toHaveProperty("mutate");
    expect(result.current).toHaveProperty("mutateAsync");
    expect(typeof result.current.mutate).toBe("function");
  });

  it("should call createProject API and invalidate queries on success", async () => {
      const { useCreateProject } = await import("@/hooks/use-projects");
      const { projectsApi } = await import("@/lib/api-endpoints");
      const { toast } = await import("sonner");

      const newProjectData = { name: "New Project", description: "Desc", memberIds: ["u1"], color: "#000000" };
      const createdProject = { id: "p1", ...newProjectData, members: [{ userId: "u1", role: "member" }] };

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      vi.mocked(projectsApi.createProject).mockResolvedValue(createdProject as any);

      const { result } = renderHook(() => useCreateProject(), {
          wrapper: createWrapper(),
      });

      await result.current.mutateAsync(newProjectData);

      expect(projectsApi.createProject).toHaveBeenCalledWith(expect.objectContaining({
          name: "New Project",
          members: [{ userId: "u1", role: "member" }]
      }));
      expect(toast.success).toHaveBeenCalled();
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

  it("should call updateProject API and show success toast", async () => {
      const { useUpdateProject } = await import("@/hooks/use-projects");
      const { projectsApi } = await import("@/lib/api-endpoints");
      const { toast } = await import("sonner");

      const updateData = { id: "p1", data: { name: "Updated Name", status: ProjectStatus.ACTIVE } };
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      vi.mocked(projectsApi.updateProject).mockResolvedValue({ id: "p1", name: "Updated Name" } as any);

      const { result } = renderHook(() => useUpdateProject(), {
          wrapper: createWrapper(),
      });

      await result.current.mutateAsync(updateData);

      expect(projectsApi.updateProject).toHaveBeenCalledWith("p1", expect.objectContaining({
          name: "Updated Name",
          is_active: true
      }));
      expect(toast.success).toHaveBeenCalled();
  });

  it("should map frontend project fields to the backend update contract", async () => {
      const { useUpdateProject } = await import("@/hooks/use-projects");
      const { projectsApi } = await import("@/lib/api-endpoints");

      vi.mocked(projectsApi.updateProject).mockResolvedValue(
        { id: "p1", name: "Updated" } as unknown as Project,
      );

      const { result } = renderHook(() => useUpdateProject(), {
          wrapper: createWrapper(),
      });

      await result.current.mutateAsync({
          id: "p1",
          data: {
              name: "Updated",
              color: "#123456",
              memberIds: ["u1"],
              settings: { defaultTaskVisibility: "private" },
          },
      });

      expect(projectsApi.updateProject).toHaveBeenCalledWith("p1", {
          name: "Updated",
          color: "#123456",
          member_ids: ["u1"],
          settings: { defaultTaskVisibility: "private" },
      });
  });
});

describe("useArchiveProject Hook", () => {
    it("should call updateProject API with is_active: false", async () => {
        const { useArchiveProject } = await import("@/hooks/use-projects");
        const { projectsApi } = await import("@/lib/api-endpoints");
        const { toast } = await import("sonner");

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const projectToArchive = { id: "p1", name: "To Archive" } as any;
        vi.mocked(projectsApi.updateProject).mockResolvedValue({ ...projectToArchive, is_active: false });

        const { result } = renderHook(() => useArchiveProject(), {
            wrapper: createWrapper(),
        });

        await result.current.mutateAsync(projectToArchive);

        expect(projectsApi.updateProject).toHaveBeenCalledWith("p1", expect.objectContaining({
            is_active: false
        }));
        expect(toast.success).toHaveBeenCalled();
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
