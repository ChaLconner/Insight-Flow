"use client";

import { useState, useEffect, useRef, useCallback, forwardRef, useImperativeHandle, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Search,
    Plus,
    CheckCircle2,
    ChevronLeft,
    ChevronRight,
    Loader2
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import type { Task } from "@/types";
import { useAuthStore } from "@/stores/auth-store";
import { tasksApi } from "@/lib/api-endpoints";
import { apiClient } from "@/lib/api-client";
import { NewTaskModal } from "./NewTaskModal";
import { CustomSelect } from "@/components/ui/custom-select";
import { TaskItem } from "./TaskItem";
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";

export interface TaskListRef {
    refresh: () => void;
}

interface TaskListProps {
    projectId?: string;
    showProjectName?: boolean;
    title?: string;
    description?: string;
    hideHeader?: boolean;
    onTaskChange?: () => void;
}

export const TaskList = forwardRef<TaskListRef, TaskListProps>(({
    projectId,
    showProjectName = true,
    title = "Tasks",
    description = "Manage and track your tasks.",
    hideHeader = false,
    onTaskChange
}, ref) => {
    const [isNewTaskModalOpen, setIsNewTaskModalOpen] = useState(false);
    const [editingTask, setEditingTask] = useState<Task | null>(null);
    const [openMenuId, setOpenMenuId] = useState<string | null>(null);
    const [localSearchQuery, setLocalSearchQuery] = useState("");

    const searchParams = useSearchParams();
    const router = useRouter();
    const queryClient = useQueryClient();

    // Initialize state from URL params with memoization
    const [searchQuery, setSearchQuery] = useState(() => searchParams.get("search") || "");
    const [statusFilter, setStatusFilter] = useState<string>(() => searchParams.get("status") || "all");
    const [page, setPage] = useState(() => {
        const pageParam = searchParams.get("page");
        return pageParam ? parseInt(pageParam, 10) : 1;
    });

    const PAGE_SIZE = 10; // Show 10 items per page

    const { isAuthenticated } = useAuthStore();

    // Refs
    const isMounted = useRef(true);
    const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    // Debounced search function
    const debouncedSearch = useCallback((query: string) => {
        if (searchTimeoutRef.current) {
            clearTimeout(searchTimeoutRef.current);
        }

        searchTimeoutRef.current = setTimeout(() => {
            setSearchQuery(query);
            setPage(1); // Reset to first page when searching
        }, 500); // 500ms debounce
    }, []);

    // Update URL when filters change
    useEffect(() => {
        const params = new URLSearchParams();
        if (searchQuery) params.set("search", searchQuery);
        if (statusFilter !== "all") params.set("status", statusFilter);
        if (page > 1) params.set("page", page.toString());

        const newUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ''}`;
        router.replace(newUrl, { scroll: false });
    }, [searchQuery, statusFilter, page, router]);

    useEffect(() => {
        isMounted.current = true;
        return () => {
            isMounted.current = false;
        };
    }, []);

    // Create query key with memoization for better performance
    const queryKey = useMemo(() => [
        'tasks',
        projectId || 'my',
        page,
        PAGE_SIZE,
        searchQuery,
        statusFilter
    ], [projectId, page, searchQuery, statusFilter]);

    // Sync state from URL params when navigating (e.g. back button)
    useEffect(() => {
        const query = searchParams.get("search") || "";
        const status = searchParams.get("status") || "all";
        const pageParam = searchParams.get("page");
        const newPage = pageParam ? parseInt(pageParam, 10) : 1;

        if (query !== searchQuery) setSearchQuery(query);
        if (query !== localSearchQuery) setLocalSearchQuery(query);
        if (status !== statusFilter) setStatusFilter(status);
        if (newPage !== page) setPage(newPage);
    }, [searchParams]); // Only run when URL params change

    // React Query for data fetching with caching
    const {
        data: tasksData = [],
        isLoading,
        error,
        refetch,
        isFetching
    } = useQuery<Task[]>({
        queryKey,
        queryFn: async () => {
            if (!isAuthenticated) return [];

            const skip = (page - 1) * PAGE_SIZE;
            const limit = PAGE_SIZE;

            console.log('TaskList: Fetching tasks...', { projectId, skip, limit, searchQuery, statusFilter });

            let data;
            if (projectId) {
                // Fetch tasks for specific project
                data = await tasksApi.getProjectTasks(
                    projectId,
                    skip,
                    limit,
                    undefined, // sortBy
                    undefined, // sortOrder
                    searchQuery,
                    statusFilter
                );
            } else {
                // Fetch all user tasks
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

            console.log('TaskList: Fetched successfully', taskList.length);
            return taskList;
        },
        enabled: isAuthenticated,
        staleTime: 30 * 1000, // 30 seconds
        gcTime: 5 * 60 * 1000, // 5 minutes (gcTime replaced cacheTime in v5)
        retry: 2,
        refetchOnWindowFocus: false,
    });

    // Extract tasks from data
    const tasks = tasksData || [];

    // Delete task mutation
    const deleteTaskMutation = useMutation({
        mutationFn: async (task: Task) => {
            if (task.projectId) {
                await tasksApi.deleteProjectTask(task.projectId, task.id);
            } else {
                await tasksApi.deleteTask(task.id);
            }
            return task.id;
        },
        onSuccess: () => {
            // Invalidate and refetch
            setOpenMenuId(null);
            const qKey = projectId ? ['tasks', projectId] : ['tasks', 'my'];
            queryClient.invalidateQueries({ queryKey: qKey });
            queryClient.invalidateQueries({ queryKey: ['tasks', 'my'] }); // Always invalidate global list too
            if (onTaskChange) onTaskChange();

            toast.success("Task deleted", {
                description: "The task has been permanently removed.",
            });
        },
    });

    // Handle refresh logic exposed to parent
    useImperativeHandle(ref, () => ({
        refresh: () => {
            refetch();
        }
    }));

    // Other handlers
    const handleTaskClick = useCallback((task: Task) => {
        if (task.projectId) {
            router.push(`/projects/${task.projectId}/tasks/${task.id}`);
        }
    }, [router]);

    const handleEditTask = useCallback((task: Task) => {
        setEditingTask(task);
        setIsNewTaskModalOpen(true);
        setOpenMenuId(null);
    }, []);

    const handleDeleteTask = useCallback(async (task: Task) => {
        if (!confirm("Are you sure you want to delete this task?")) return;

        try {
            await deleteTaskMutation.mutateAsync(task);
        } catch (err: any) {
            console.error("Failed to delete task", err);
            toast.error("Failed to delete task", {
                description: getErrorMessage(err)
            });
        }
    }, [deleteTaskMutation]);

    const toggleMenu = useCallback((e: React.MouseEvent, taskId: string) => {
        e.stopPropagation();
        setOpenMenuId(prev => (prev === taskId ? null : taskId));
    }, []);

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (!openMenuId) return;

            // Handle text nodes (e.g. clicking text inside button)
            let target = event.target as Node;
            if (target.nodeType === Node.TEXT_NODE) {
                target = target.parentNode as Node;
            }

            const element = target as Element;

            // Safety check for .closest method
            if (!element || typeof element.closest !== 'function') {
                return;
            }

            if (
                !element.closest('.task-menu-trigger') &&
                !element.closest('.task-menu-dropdown')
            ) {
                setOpenMenuId(null);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [openMenuId]);


    // RENDER LOGIC
    if (isLoading && !isFetching && tasks.length === 0) {
        return (
            <div className="space-y-8">
                {/* Header Skeleton */}
                {!hideHeader && (
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                        <div className="space-y-2">
                            <Skeleton className="h-8 w-48" />
                            <Skeleton className="h-4 w-64" />
                        </div>
                        <div className="flex gap-2 w-full sm:w-auto">
                            <Skeleton className="h-10 w-24" />
                            <Skeleton className="h-10 w-32" />
                        </div>
                    </div>
                )}
                {/* List Skeleton */}
                <div className="space-y-4">
                    {[...Array(5)].map((_, i) => (
                        <Card key={i} className="border-white/10 bg-white/5">
                            <CardContent className="p-4">
                                <div className="flex gap-4">
                                    <Skeleton className="h-4 w-4 rounded-full" />
                                    <div className="flex-1 space-y-2">
                                        <Skeleton className="h-4 w-1/3" />
                                        <Skeleton className="h-3 w-1/4" />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        const errorMessage = typeof error === 'string' ? error :
            (error as any)?.message || 'Failed to load tasks.';

        return (
            <div className="flex flex-col items-center justify-center h-64 space-y-4">
                <div className="text-red-400 text-center">
                    <p className="text-lg font-medium">{errorMessage}</p>
                    <Button onClick={() => refetch()}>Retry</Button>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Header */}
            {!hideHeader && (
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div>
                        <h2 className="text-3xl font-bold tracking-tight text-white">{title}</h2>
                        <p className="mt-1 text-zinc-400">{description}</p>
                    </div>
                    <div className="flex gap-2 w-full sm:w-auto">

                        <Button
                            className="flex-1 sm:flex-none bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-500/20"
                            onClick={() => {
                                setEditingTask(null);
                                setIsNewTaskModalOpen(true);
                            }}
                        >
                            <Plus className="h-4 w-4 mr-2" />
                            New Task
                        </Button>
                    </div>
                </div>
            )}

            {/* Search and Filter Controls */}
            <div className="flex flex-col sm:flex-row gap-4 mb-6">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
                    <Input
                        placeholder="Search tasks..."
                        value={localSearchQuery}
                        onChange={(e) => {
                            setLocalSearchQuery(e.target.value);
                            debouncedSearch(e.target.value);
                        }}
                        className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-zinc-400"
                    />
                </div>
                <CustomSelect
                    value={statusFilter}
                    onChange={(value: string) => {
                        setStatusFilter(value);
                        setPage(1); // Reset to first page when filtering
                    }}
                    options={[
                        { value: "all", label: "All Status" },
                        { value: "todo", label: "To Do" },
                        { value: "in_progress", label: "In Progress" },
                        { value: "done", label: "Done" },
                    ]}
                    className="w-full sm:w-48"
                />
            </div>

            {/* Content */}
            <div className="space-y-4">
                {tasks.length > 0 ? (
                    tasks.map((task) => (
                        <TaskItem
                            key={task.id}
                            task={task}
                            showProjectName={showProjectName}
                            isOpen={openMenuId === task.id}
                            isDeleting={deleteTaskMutation.isPending}
                            onToggleMenu={toggleMenu}
                            onEdit={handleEditTask}
                            onDelete={handleDeleteTask}
                            onClick={handleTaskClick}
                        />
                    ))
                ) : (
                    <div className="text-center py-12 text-zinc-400">
                        <CheckCircle2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <h3 className="text-lg font-medium text-white">No tasks found</h3>
                        <p>Try adjusting your search or filters.</p>
                    </div>
                )}
            </div>

            {/* Pagination Controls */}
            {tasks.length > 0 && (
                <div className="flex justify-between items-center mt-8">
                    <div className="text-sm text-zinc-400">
                        Showing {((page - 1) * PAGE_SIZE) + 1} to {((page - 1) * PAGE_SIZE) + tasks.length} tasks
                    </div>
                    <div className="flex gap-2">
                        <Button
                            variant="glass"
                            size="sm"
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                            className="flex items-center gap-2 text-white font-medium border-white/10 hover:bg-white/10"
                        >
                            <ChevronLeft className="h-4 w-4" />
                            Previous
                        </Button>
                        <div className="flex items-center px-4 py-1 bg-white/10 rounded-md border border-white/20 shadow-sm">
                            <span className="text-sm font-bold text-white tracking-wide">Page {page}</span>
                        </div>
                        <Button
                            variant="glass"
                            size="sm"
                            onClick={() => setPage(p => p + 1)}
                            disabled={tasks.length < PAGE_SIZE}
                            className="flex items-center gap-2 text-white font-medium border-white/10 hover:bg-white/10"
                        >
                            Next
                            <ChevronRight className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            )}

            <NewTaskModal
                isOpen={isNewTaskModalOpen}
                onClose={() => {
                    setIsNewTaskModalOpen(false);
                    setEditingTask(null);
                }}
                onTaskCreated={() => {
                    const qKey = projectId ? ['tasks', projectId] : ['tasks', 'my'];
                    queryClient.invalidateQueries({ queryKey: qKey });
                    queryClient.invalidateQueries({ queryKey: ['tasks', 'my'] }); // Always invalidate global list too
                    setIsNewTaskModalOpen(false);
                    setEditingTask(null);
                    if (onTaskChange) onTaskChange();
                }}
                defaultProjectId={projectId}
                task={editingTask}
            />
        </div>
    );
});

TaskList.displayName = "TaskList";
