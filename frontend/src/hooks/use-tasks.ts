import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tasksApi } from "@/lib/api-endpoints";
import type { Task, TaskListResponse } from "@/types";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";
import { useAuthStore } from "@/stores/auth-store";

interface UseTasksOptions {
  projectId?: string;
  page?: number;
  pageSize?: number;
  searchQuery?: string;
  statusFilter?: string;
  enabled?: boolean;
}

export const useTasks = ({
  projectId,
  page = 1,
  pageSize = 10,
  searchQuery = "",
  statusFilter = "all",
  enabled = true,
}: UseTasksOptions = {}) => {
  const queryClient = useQueryClient();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const queryKey = [
    "tasks",
    projectId ?? "my",
    page,
    pageSize,
    searchQuery,
    statusFilter,
  ];

  const {
    data: taskResponse,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery<TaskListResponse>({
    queryKey,
    queryFn: async () => {
      if (!isAuthenticated) {
        return { items: [], total: 0, page: 1, size: pageSize, hasMore: false };
      }

      const skip = (page - 1) * pageSize;
      const limit = pageSize;

      const data = projectId
        ? await tasksApi.getProjectTasks(
            projectId,
            skip,
            limit,
            undefined,
            undefined,
            searchQuery,
            statusFilter,
          )
        : await tasksApi.getMyTasks(skip, limit, searchQuery, statusFilter);

      // Standard response format
      if (data && "items" in data) {
        return data as unknown as TaskListResponse;
      }

      // Handle legacy array responses with unified fallback
      const items: Task[] = Array.isArray(data)
        ? data
        : (data as { data?: Task[]; tasks?: Task[] })?.data ??
          (data as { tasks?: Task[] })?.tasks ??
          [];

      return {
        items,
        total: items.length,
        page,
        size: pageSize,
        hasMore: items.length >= pageSize,
      };
    },
    enabled: Boolean(enabled && isAuthenticated),
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    retry: 2,
    refetchOnWindowFocus: false,
  });

  // Helper to get items safely
  const tasks = taskResponse?.items ?? [];
  const total = taskResponse?.total ?? 0;
  const hasMore =
    taskResponse?.hasMore ??
    (taskResponse as (TaskListResponse & { has_more?: boolean }) | undefined)
      ?.has_more ??
    false;

  const updateTaskMutation = useMutation({
    mutationFn: async (task: Partial<Task> & { id: string }) => {
      const { id, ...updates } = task;
      // Determine project ID from cache or context if not provided
      // For now, simpler to assume updateTask API handles validation
      // But API requires projectId for project tasks?
      // The Task type usually has projectId.
      // Let's assume the API client handles the distinction or we pass it.
      // tasksApi.updateTask handles it logic ally.
      if (task.projectId) {
        return tasksApi.updateProjectTask(task.projectId, id, updates);
      } else {
        return tasksApi.updateTask(id, updates);
      }
    },
    onMutate: async (updatedTask) => {
      await queryClient.cancelQueries({ queryKey });
      const previousData = queryClient.getQueryData<TaskListResponse>(queryKey);

      if (previousData) {
        queryClient.setQueryData<TaskListResponse>(queryKey, (old) => {
          if (!old) {
            return old;
          }
          return {
            ...old,
            items: old.items.map((t) =>
              t.id === updatedTask.id ? { ...t, ...updatedTask } : t,
            ),
          };
        });
      }
      return { previousData };
    },
    onError: (err, newTodo, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
      toast.error("Failed to update task", {
        description: getErrorMessage(err),
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const deleteTaskMutation = useMutation({
    mutationFn: async (task: Task) => {
      if (task.projectId) {
        await tasksApi.deleteProjectTask(task.projectId, task.id);
      } else {
        await tasksApi.deleteTask(task.id);
      }
      return task.id;
    },
    onMutate: async (deletedTask) => {
      await queryClient.cancelQueries({ queryKey });
      const previousData = queryClient.getQueryData<TaskListResponse>(queryKey);

      if (previousData) {
        queryClient.setQueryData<TaskListResponse>(queryKey, (old) => {
          if (!old) {
            return old;
          }
          return {
            ...old,
            items: old.items.filter((t) => t.id !== deletedTask.id),
            total: old.total - 1,
          };
        });
      }
      return { previousData };
    },
    onSuccess: () => {
      // onMutate handles the UI. onSuccess just confirms/invalidates.
      toast.success("Task deleted", {
        description: "The task has been permanently removed.",
      });
    },
    onError: (err, variables, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
      console.error("Failed to delete task", err);
      toast.error("Failed to delete task", {
        description: getErrorMessage(err),
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  return {
    tasks,
    total,
    hasMore,
    isLoading,
    isFetching,
    error,
    refetch,
    deleteTask: deleteTaskMutation.mutate,
    isDeleting: deleteTaskMutation.isPending,
    updateTask: updateTaskMutation.mutate,
    isUpdating: updateTaskMutation.isPending,
  };
};
