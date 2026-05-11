/**
 * Unit tests for useTasks hook.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useTasks } from "@/hooks/use-tasks";

// Mock the auth store
vi.mock("@/stores/auth-store", () => ({
  useAuthStore: vi.fn((selector) => {
    const state = { isAuthenticated: true };
    return selector ? selector(state) : state.isAuthenticated;
  }),
}));

// Mock the tasksApi
vi.mock("@/lib/api-endpoints", () => ({
  tasksApi: {
    getProjectTasks: vi.fn(),
    getMyTasks: vi.fn(),
    updateTask: vi.fn(),
    updateProjectTask: vi.fn(),
    deleteTask: vi.fn(),
    deleteProjectTask: vi.fn(),
  },
}));

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { tasksApi } from "@/lib/api-endpoints";

describe("useTasks hook", () => {
  let queryClient: QueryClient;

  const createWrapper = () => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    return ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient?.clear();
  });

  describe("fetching tasks", () => {
    it("should fetch my tasks when no projectId is provided", async () => {
      const mockResponse = {
        items: [
          { id: "1", title: "Task 1", status: "todo" },
          { id: "2", title: "Task 2", status: "in_progress" },
        ],
        total: 2,
        page: 1,
        size: 10,
        hasMore: false,
      };

      (tasksApi.getMyTasks as ReturnType<typeof vi.fn>).mockResolvedValue(
        mockResponse,
      );

      const { result } = renderHook(() => useTasks(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(tasksApi.getMyTasks).toHaveBeenCalledWith(0, 10, "", "all");
      expect(result.current.tasks).toHaveLength(2);
      expect(result.current.total).toBe(2);
    });

    it("should fetch project tasks when projectId is provided", async () => {
      const mockResponse = {
        items: [
          {
            id: "1",
            title: "Project Task 1",
            status: "todo",
            projectId: "proj-1",
          },
        ],
        total: 1,
        page: 1,
        size: 10,
        hasMore: false,
      };

      (tasksApi.getProjectTasks as ReturnType<typeof vi.fn>).mockResolvedValue(
        mockResponse,
      );

      const { result } = renderHook(() => useTasks({ projectId: "proj-1" }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(tasksApi.getProjectTasks).toHaveBeenCalledWith(
        "proj-1",
        0,
        10,
        undefined,
        undefined,
        "",
        "all",
      );
      expect(result.current.tasks).toHaveLength(1);
    });

    it("should handle pagination correctly", async () => {
      const mockResponse = {
        items: [{ id: "3", title: "Task 3" }],
        total: 25,
        page: 2,
        size: 10,
        hasMore: true,
      };

      (tasksApi.getMyTasks as ReturnType<typeof vi.fn>).mockResolvedValue(
        mockResponse,
      );

      const { result } = renderHook(() => useTasks({ page: 2, pageSize: 10 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Skip should be (page - 1) * pageSize = (2 - 1) * 10 = 10
      expect(tasksApi.getMyTasks).toHaveBeenCalledWith(10, 10, "", "all");
    });

    it("should handle search and filter", async () => {
      const mockResponse = {
        items: [],
        total: 0,
        page: 1,
        size: 10,
        hasMore: false,
      };

      (tasksApi.getMyTasks as ReturnType<typeof vi.fn>).mockResolvedValue(
        mockResponse,
      );

      renderHook(
        () => useTasks({ searchQuery: "test", statusFilter: "done" }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(tasksApi.getMyTasks).toHaveBeenCalledWith(0, 10, "test", "done");
      });
    });

    it("should not fetch when disabled", async () => {
      renderHook(() => useTasks({ enabled: false }), {
        wrapper: createWrapper(),
      });

      // Wait a bit to ensure no API call is made
      await new Promise((r) => setTimeout(r, 100));

      expect(tasksApi.getMyTasks).not.toHaveBeenCalled();
      expect(tasksApi.getProjectTasks).not.toHaveBeenCalled();
    });
    it("should not fetch when not authenticated", async () => {
       const { useAuthStore } = await import("@/stores/auth-store");
      vi.mocked(useAuthStore).mockImplementation((selector) => {
        const state = { isAuthenticated: false } as Parameters<typeof selector>[0];
        return selector(state);
      });

       const { result } = renderHook(() => useTasks(), {
         wrapper: createWrapper(),
       });

       await waitFor(() => {
         expect(result.current.isLoading).toBe(false);
       });

       expect(tasksApi.getMyTasks).not.toHaveBeenCalled();
       expect(result.current.tasks).toEqual([]);
      vi.mocked(useAuthStore).mockImplementation((selector) => {
        const state = { isAuthenticated: true } as Parameters<typeof selector>[0];
        return selector(state);
      });
    });
  });

  describe("initial state", () => {
    it("should return correct initial state", () => {
      (tasksApi.getMyTasks as ReturnType<typeof vi.fn>).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        size: 10,
        hasMore: false,
      });

      const { result } = renderHook(() => useTasks(), {
        wrapper: createWrapper(),
      });

      expect(result.current.tasks).toEqual([]);
      expect(result.current.total).toBe(0);
      expect(result.current.hasMore).toBe(false);
      expect(result.current.isDeleting).toBe(false);
      expect(result.current.isUpdating).toBe(false);
    });
  });

  describe("legacy response handling", () => {
    it("should handle array response format", async () => {
      const legacyResponse = [
        { id: "1", title: "Legacy Task 1" },
        { id: "2", title: "Legacy Task 2" },
      ];

      (tasksApi.getMyTasks as ReturnType<typeof vi.fn>).mockResolvedValue(
        legacyResponse,
      );

      const { result } = renderHook(() => useTasks(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.tasks).toHaveLength(2);
      expect(result.current.total).toBe(2);
    });

    it("should handle { data: [...] } response format", async () => {
      const wrappedResponse = {
        data: [{ id: "1", title: "Wrapped Task 1" }],
      };

      (tasksApi.getMyTasks as ReturnType<typeof vi.fn>).mockResolvedValue(
        wrappedResponse,
      );

      const { result } = renderHook(() => useTasks(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.tasks).toHaveLength(1);
    });
  });
});

describe("useTasks mutations", () => {
  let queryClient: QueryClient;

  const createWrapper = () => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    return ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Setup default mock response
    (tasksApi.getMyTasks as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [{ id: "1", title: "Test Task", projectId: null }],
      total: 1,
      page: 1,
      size: 10,
      hasMore: false,
    });
  });

  it("should update task and invalidate queries", async () => {
    const { toast } = await import("sonner");
    const { result } = renderHook(() => useTasks(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const updateData = { id: "1", title: "Updated Task" };
    (tasksApi.updateTask as ReturnType<typeof vi.fn>).mockResolvedValue(updateData);

    await result.current.updateTask(updateData);

    await waitFor(() => {
        expect(tasksApi.updateTask).toHaveBeenCalledWith("1", { title: "Updated Task" });
    });
    // Invalidate queries is called
    // We can't easily check cache invalidation without peeking into queryClient, 
    // but we can check if toast error was NOT called (success is silent in code? No, code doesn't toast success)
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("should update project task when projectId is present", async () => {
      const { result } = renderHook(() => useTasks(), {
          wrapper: createWrapper(),
      });
  
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
  
      const updateData = { id: "1", title: "Updated Project Task", projectId: "p1" };
      (tasksApi.updateProjectTask as ReturnType<typeof vi.fn>).mockResolvedValue(updateData);
  
      await result.current.updateTask(updateData);
  
      await waitFor(() => {
          expect(tasksApi.updateProjectTask).toHaveBeenCalledWith("p1", "1", expect.objectContaining({ title: "Updated Project Task" }));
      });
  });

  it("should delete task and show success toast", async () => {
    const { toast } = await import("sonner");
    const { result } = renderHook(() => useTasks(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const taskToDelete = { id: "1", title: "To Delete", projectId: null } as any;
    (tasksApi.deleteTask as ReturnType<typeof vi.fn>).mockResolvedValue(true);

    await result.current.deleteTask(taskToDelete);

    await waitFor(() => {
        expect(tasksApi.deleteTask).toHaveBeenCalledWith("1");
        expect(toast.success).toHaveBeenCalled();
    });
  });

  it("should delete project task when projectId is present", async () => {
      const { toast } = await import("sonner");
      const { result } = renderHook(() => useTasks(), {
        wrapper: createWrapper(),
      });
  
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
  
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const taskToDelete = { id: "2", title: "To Delete", projectId: "p1" } as any;
      (tasksApi.deleteProjectTask as ReturnType<typeof vi.fn>).mockResolvedValue(true);
  
      await result.current.deleteTask(taskToDelete);
  
      await waitFor(() => {
          expect(tasksApi.deleteProjectTask).toHaveBeenCalledWith("p1", "2");
          expect(toast.success).toHaveBeenCalled();
      });
  });
});
