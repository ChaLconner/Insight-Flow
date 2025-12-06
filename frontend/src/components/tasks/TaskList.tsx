"use client";

import { useState, useEffect, useRef, useCallback, forwardRef, useImperativeHandle } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
    Search,
    Filter,
    Plus,
    MoreHorizontal,
    Calendar,
    CheckCircle2,
    User as UserIcon,
    RefreshCw,
    ChevronLeft,
    ChevronRight,
    Edit,
    Trash2
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { Skeleton } from "@/components/ui/skeleton";
import type { Task } from "@/types";
import { useAuthStore } from "@/stores/auth-store";
import { tasksApi } from "@/lib/api-endpoints";
import { format } from "date-fns";
import { NewTaskModal } from "./NewTaskModal";
import { CustomSelect } from "@/components/ui/custom-select";
import { getAvatarUrl } from "@/lib/utils";
import { TaskItem } from "./TaskItem";

export interface TaskListRef {
    refresh: () => void;
}

interface TaskListProps {
    projectId?: string;
    showProjectName?: boolean;
    title?: string;
    description?: string;
    hideHeader?: boolean;
}

export const TaskList = forwardRef<TaskListRef, TaskListProps>(({
    projectId,
    showProjectName = true,
    title = "Tasks",
    description = "Manage and track your tasks.",
    hideHeader = false
}, ref) => {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isNewTaskModalOpen, setIsNewTaskModalOpen] = useState(false);
    const searchParams = useSearchParams();
    const router = useRouter();
    const [searchQuery, setSearchQuery] = useState(searchParams.get("search") || "");
    const [statusFilter, setStatusFilter] = useState<string>("all");
    const [page, setPage] = useState(1);
    const PAGE_SIZE = 10;
    const [editingTask, setEditingTask] = useState<Task | null>(null);
    const [openMenuId, setOpenMenuId] = useState<string | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const { isAuthenticated } = useAuthStore();
    // Refs to prevent duplicate API calls and handle unmounting
    const isLoadingRef = useRef(false);
    const hasLoadedOnce = useRef(false);
    const lastLoadTime = useRef<number>(0);
    const isMounted = useRef(true);

    useEffect(() => {
        return () => {
            isMounted.current = false;
        };
    }, []);

    // Debounce search query
    useEffect(() => {
        const timer = setTimeout(() => {
            if (hasLoadedOnce.current) {
                setPage(1); // Reset to page 1 on search change
                loadTasks(true);
            }
        }, 500);
        return () => clearTimeout(timer);
    }, [searchQuery]);

    // Relaxes status filter
    useEffect(() => {
        if (hasLoadedOnce.current) {
            setPage(1); // Reset to page 1 on filter change
            loadTasks(true);
        }
    }, [statusFilter]);

    const loadTasks = useCallback(async (forceRefresh = false) => {
        if (!isAuthenticated) {
            return;
        }

        // Rate limiting logic...
        const now = Date.now();
        if (!forceRefresh && now - lastLoadTime.current < 300) {
            return;
        }

        // Prevent duplicate concurrent calls
        if (isLoadingRef.current) {
            return;
        }

        try {
            isLoadingRef.current = true;
            lastLoadTime.current = now;

            if (forceRefresh) {
                setRefreshing(true);
            } else {
                setLoading(true);
            }
            setError(null);

            let response;
            const skip = (page - 1) * PAGE_SIZE;
            const limit = PAGE_SIZE;

            if (projectId) {
                // Pass search and status to project tasks API
                response = await tasksApi.getProjectTasks(
                    projectId,
                    skip,
                    limit,
                    undefined,
                    undefined,
                    searchQuery,
                    statusFilter
                );
            } else {
                // Pass search and status to user tasks API
                response = await tasksApi.getTasks(skip, limit, searchQuery, statusFilter);
            }

            if (isMounted.current) {
                // Handle paginated response or array
                const taskList = Array.isArray(response) ? response : (response as { data?: Task[] }).data ?? [];
                setTasks(taskList);
                hasLoadedOnce.current = true;
            }
        } catch (err) {
            console.error('Error loading tasks:', err);
            if (isMounted.current) {
                setError('Failed to load tasks');
            }
        } finally {
            isLoadingRef.current = false;
            if (isMounted.current) {
                setLoading(false);
                setRefreshing(false);
            }
        }
    }, [isAuthenticated, projectId, page, searchQuery, statusFilter]);

    useImperativeHandle(ref, () => ({
        refresh: () => {
            loadTasks(true);
        }
    }));

    useEffect(() => {
        if (isAuthenticated && !hasLoadedOnce.current) {
            loadTasks();
        }
    }, [isAuthenticated, loadTasks]);

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (openMenuId && !(event.target as Element).closest('.task-menu-trigger')) {
                setOpenMenuId(null);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [openMenuId]);

    const handleRefresh = () => {
        loadTasks(true);
    };

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

        setDeletingId(task.id);
        setOpenMenuId(null);
        try {
            if (task.projectId) {
                await tasksApi.deleteProjectTask(task.projectId, task.id);
            } else {
                await tasksApi.deleteTask(task.id);
            }
            loadTasks(true);
        } catch (err) {
            console.error("Failed to delete task", err);
            // Optionally show error toast
        } finally {
            setDeletingId(null);
        }
    }, [loadTasks]);

    const toggleMenu = useCallback((e: React.MouseEvent, taskId: string) => {
        e.stopPropagation();
        setOpenMenuId(prev => (prev === taskId ? null : taskId));
    }, []);

    const filteredTasks = tasks;
    if (loading) {
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

                {/* Search and Filter Skeleton */}
                <div className="flex flex-col sm:flex-row gap-4">
                    <Skeleton className="h-10 flex-1" />
                    <div className="flex gap-2">
                        <Skeleton className="h-10 w-32" />
                        <Skeleton className="h-10 w-32" />
                    </div>
                </div>

                {/* Tasks List Skeleton */}
                <div className="space-y-4">
                    {[...Array(5)].map((_, i) => (
                        <Card key={i} className="border-white/10 bg-white/5 backdrop-blur-sm">
                            <CardContent className="p-4 flex items-center justify-between gap-4">
                                <div className="flex items-center gap-4 flex-1 min-w-0">
                                    <Skeleton className="h-2 w-2 rounded-full" />
                                    <div className="min-w-0 flex-1 space-y-2">
                                        <Skeleton className="h-5 w-1/3" />
                                        <div className="flex items-center gap-4">
                                            <Skeleton className="h-3 w-24" />
                                            <Skeleton className="h-3 w-24" />
                                            <Skeleton className="h-3 w-24" />
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <Skeleton className="h-6 w-20 rounded-full" />
                                    <Skeleton className="h-8 w-8 rounded-lg" />
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-64 space-y-4">
                <div className="text-red-400 text-center">
                    <p className="text-lg font-medium">{error}</p>
                    <button
                        onClick={() => loadTasks()}
                        className="mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
                    >
                        Retry
                    </button>
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
                        <p className="mt-1 text-zinc-400">
                            {description}
                        </p>
                    </div>
                    <div className="flex gap-2 w-full sm:w-auto">
                        <Button
                            variant="outline"
                            onClick={handleRefresh}
                            disabled={refreshing}
                            className="flex-1 sm:flex-none bg-transparent border-white/20 text-white hover:bg-white/10 hover:text-white hover:border-white/30 transition-all"
                        >
                            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                            {refreshing ? 'Refreshing...' : 'Refresh'}
                        </Button>
                        <Button
                            className="flex-1 sm:flex-none bg-indigo-600 hover:bg-indigo-500 text-white"
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

            {/* Search and Filter */}
            <div className="flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" aria-hidden="true" />
                    <Input
                        placeholder="Search tasks..."
                        aria-label="Search tasks"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-zinc-400"
                    />
                </div>
                <div className="flex flex-col sm:flex-row gap-2">
                    <CustomSelect
                        value={statusFilter}
                        onChange={(value) => setStatusFilter(value)}
                        options={[
                            { value: "all", label: "All Status" },
                            { value: "todo", label: "To Do" },
                            { value: "in_progress", label: "In Progress" },
                            { value: "in_review", label: "In Review" },
                            { value: "done", label: "Done" },
                            { value: "cancelled", label: "Cancelled" },
                        ]}
                        className="w-full sm:w-[140px]"
                    />

                </div>
            </div>

            {/* Tasks List */}
            <div className="space-y-4">
                <AnimatePresence mode="popLayout">
                    {filteredTasks.length > 0 ? (
                        filteredTasks.map((task) => (
                            <motion.div
                                key={task.id}
                                layout
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                transition={{ duration: 0.2 }}
                            >
                                <TaskItem
                                    task={task}
                                    showProjectName={!!showProjectName}
                                    isOpen={openMenuId === task.id}
                                    isDeleting={deletingId === task.id}
                                    onToggleMenu={toggleMenu}
                                    onEdit={handleEditTask}
                                    onDelete={handleDeleteTask}
                                    onClick={handleTaskClick}
                                />
                            </motion.div>
                        ))
                    ) : (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ duration: 0.3 }}
                            className="text-center py-12"
                        >
                            <div className="mx-auto h-12 w-12 rounded-full bg-white/5 flex items-center justify-center mb-4">
                                <CheckCircle2 className="h-6 w-6 text-zinc-400" />
                            </div>
                            <h3 className="text-lg font-medium text-white mb-2">No tasks found</h3>
                            <p className="text-zinc-400 mb-6">
                                {searchQuery || statusFilter !== "all"
                                    ? "Try adjusting your search or filter criteria."
                                    : "Get started by creating your first task."}
                            </p>
                            {!searchQuery && statusFilter === "all" && (
                                <Button
                                    className="bg-indigo-600 hover:bg-indigo-500 text-white"
                                    onClick={() => {
                                        setEditingTask(null);
                                        setIsNewTaskModalOpen(true);
                                    }}
                                >
                                    <Plus className="h-4 w-4 mr-2" />
                                    Create Task
                                </Button>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-center gap-4 border-t border-white/10 pt-6 mt-6">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                        setPage(p => Math.max(1, p - 1));
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    disabled={page === 1 || loading}
                    className="text-zinc-400 hover:text-white disabled:opacity-50 hover:bg-white/5"
                >
                    <ChevronLeft className="h-4 w-4 mr-2" />
                    Previous
                </Button>

                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white bg-white/5 px-4 py-1.5 rounded-lg border border-white/10 min-w-[80px] text-center">
                        Page {page}
                    </span>
                </div>

                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                        setPage(p => p + 1);
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    disabled={tasks.length < PAGE_SIZE || loading}
                    className="text-zinc-400 hover:text-white disabled:opacity-50 hover:bg-white/5"
                >
                    Next
                    <ChevronRight className="h-4 w-4 ml-2" />
                </Button>
            </div>

            <NewTaskModal
                isOpen={isNewTaskModalOpen}
                onClose={() => {
                    setIsNewTaskModalOpen(false);
                    setEditingTask(null);
                }}
                onTaskCreated={() => {
                    loadTasks(true);
                    setIsNewTaskModalOpen(false);
                    setEditingTask(null);
                }}
                defaultProjectId={projectId}
                task={editingTask}
            />
        </div>
    );
});

TaskList.displayName = "TaskList";
