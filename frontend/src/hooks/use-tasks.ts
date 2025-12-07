import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tasksApi } from '@/lib/api-endpoints';
import { Task } from '@/types';
import { toast } from 'sonner';
import { getErrorMessage } from '@/lib/error-utils';
import { useAuthStore } from '@/stores/auth-store';

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
    searchQuery = '',
    statusFilter = 'all',
    enabled = true,
}: UseTasksOptions = {}) => {
    const queryClient = useQueryClient();
    const { isAuthenticated } = useAuthStore();

    const queryKey = [
        'tasks',
        projectId || 'my',
        page,
        pageSize,
        searchQuery,
        statusFilter,
    ];

    const {
        data: tasks = [],
        isLoading,
        error,
        refetch,
        isFetching,
    } = useQuery<Task[]>({
        queryKey,
        queryFn: async () => {
            if (!isAuthenticated) return [];

            const skip = (page - 1) * pageSize;
            const limit = pageSize;

            let data;
            if (projectId) {
                data = await tasksApi.getProjectTasks(
                    projectId,
                    skip,
                    limit,
                    undefined,
                    undefined,
                    searchQuery,
                    statusFilter
                );
            } else {
                data = await tasksApi.getMyTasks(skip, limit, searchQuery, statusFilter);
            }

            // Robust data extraction
            let taskList: Task[] = [];
            if (Array.isArray(data)) {
                taskList = data;
            } else if ((data as any)?.data && Array.isArray((data as any).data)) {
                taskList = (data as any).data;
            } else if ((data as any)?.tasks && Array.isArray((data as any).tasks)) {
                taskList = (data as any).tasks;
            }

            return taskList;
        },
        enabled: enabled && isAuthenticated,
        staleTime: 30 * 1000,
        gcTime: 5 * 60 * 1000,
        retry: 2,
        refetchOnWindowFocus: false,
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
        onSuccess: (taskId, variables) => {
            // Invalidate relevant queries
            const qKey = projectId ? ['tasks', projectId] : ['tasks', 'my'];
            queryClient.invalidateQueries({ queryKey: qKey });
            queryClient.invalidateQueries({ queryKey: ['tasks', 'my'] });

            toast.success('Task deleted', {
                description: 'The task has been permanently removed.',
            });
        },
        onError: (err) => {
            console.error("Failed to delete task", err);
            toast.error("Failed to delete task", {
                description: getErrorMessage(err)
            });
        }
    });

    return {
        tasks,
        isLoading,
        isFetching,
        error,
        refetch,
        deleteTask: deleteTaskMutation.mutate,
        isDeleting: deleteTaskMutation.isPending,
    };
};
