"use client";

import {
  useState,
  useEffect,
  useRef,
  useCallback,
  forwardRef,
  useImperativeHandle,
  useId,
  useMemo,
} from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Search,
  Plus,
  ChevronLeft,
  ChevronRight,
  X,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import type { Task } from "@/types";
import { useAuthStore } from "@/stores/auth-store";

// import { tasksApi } from "@/lib/api-endpoints";
// import { apiClient } from "@/lib/api-client";
import { CustomSelect } from "@/components/ui/custom-select";
import { TaskItem } from "./TaskItem";
import { useQueryClient } from "@tanstack/react-query";
import { useTasks } from "@/hooks/use-tasks";

// import { toast } from "sonner";
// import { getErrorMessage } from "@/lib/error-utils";
import dynamic from "next/dynamic";

// Optimize heavy modals with dynamic import
const NewTaskModal = dynamic(
  () => import("./NewTaskModal").then((mod) => mod.NewTaskModal),
  {
    loading: () => null,
    ssr: false,
  },
);
const DeleteTaskModal = dynamic(
  () =>
    import("@/components/modals/DeleteTaskModal").then(
      (mod) => mod.DeleteTaskModal,
    ),
  {
    loading: () => null,
    ssr: false,
  },
);

export interface TaskListRef {
  refresh: () => void;
  openNewTaskModal: () => void;
}

interface TaskListProps {
  projectId?: string;
  showProjectName?: boolean;
  title?: string;
  description?: string;
  hideHeader?: boolean;
  onTaskChange?: () => void;
}

export const TaskList = forwardRef<TaskListRef, TaskListProps>(
  (
    {
      projectId,
      showProjectName = true,
      title = "Tasks",
      description = "Manage and track your tasks.",
      hideHeader = false,
      onTaskChange,
    },
    ref,
  ) => {
    const [isNewTaskModalOpen, setIsNewTaskModalOpen] = useState(false);
    const [editingTask, setEditingTask] = useState<Task | null>(null);

    // Delete Modal State
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [taskToDelete, setTaskToDelete] = useState<Task | null>(null);

    const [openMenuId, setOpenMenuId] = useState<string | null>(null);

    const searchParams = useSearchParams();
    const router = useRouter();
    const queryClient = useQueryClient();

    // Local search state (client-side filtering like ProjectsClient)
    const [localSearchQuery, setLocalSearchQuery] = useState(
      () => searchParams.get("search") ?? "",
    );
    // Use local search directly for instant filtering (no debounce needed for client-side)

    const [statusFilter, setStatusFilter] = useState<string>(
      () => searchParams.get("status") ?? "all",
    );
    const [page, setPage] = useState(1);

    const PAGE_SIZE = 10; // Show 10 items per page
    const searchId = useId();

    const { isAuthenticated } = useAuthStore();

    // Refs
    const isMounted = useRef(true);

    const searchInputRef = useRef<HTMLInputElement>(null);

    // Focus search with shortcut
    useEffect(() => {
      const handleKeyDown = (e: KeyboardEvent) => {
        if (
          e.key === "/" &&
          document.activeElement?.tagName !== "INPUT" &&
          document.activeElement?.tagName !== "TEXTAREA" &&
          !(document.activeElement as HTMLElement)?.isContentEditable
        ) {
          e.preventDefault();
          searchInputRef.current?.focus();
        }
      };

      window.addEventListener("keydown", handleKeyDown);
      return () => window.removeEventListener("keydown", handleKeyDown);
    }, []);

    // Reset pagination when filters change
    useEffect(() => {
      setPage(1);
    }, [localSearchQuery, statusFilter]);

    // Update local search when URL param changes (e.g. from GlobalSearch)
    useEffect(() => {
      const urlSearch = searchParams.get("search");
      if (typeof urlSearch === "string" && urlSearch !== localSearchQuery) {
        setLocalSearchQuery(urlSearch);
      }
    }, [searchParams, localSearchQuery]);

    useEffect(() => {
      isMounted.current = true;
      return () => {
        isMounted.current = false;
      };
    }, []);

    // Use custom hook for data fetching and operations
    // Fetch ALL tasks without search/status params (client-side filtering)
    const {
      tasks: allTasks,
      isLoading,
      isFetching: _isFetching,
      error,
      refetch,
      deleteTask,
      isDeleting,
    } = useTasks({
      projectId,
      page: 1,
      pageSize: 1000, // Fetch all tasks for client-side filtering
      searchQuery: "", // No server-side search
      statusFilter: "all", // No server-side filter
      enabled: isAuthenticated,
    });

    // Client-side filtering (like ProjectsClient) for instant UX
    const filteredTasks = useMemo(() => {
      return allTasks.filter((task) => {
        const searchLower = localSearchQuery.toLowerCase();
        const matchesSearch =
          !localSearchQuery ||
          task.title.toLowerCase().includes(searchLower) ||
          task.description?.toLowerCase().includes(searchLower);
        const matchesStatus =
          statusFilter === "all" || task.status === statusFilter;
        return matchesSearch && matchesStatus;
      });
    }, [allTasks, localSearchQuery, statusFilter]);

    // Client-side pagination
    const paginatedTasks = useMemo(() => {
      const start = (page - 1) * PAGE_SIZE;
      return filteredTasks.slice(start, start + PAGE_SIZE);
    }, [filteredTasks, page]);

    const total = filteredTasks.length;
    const hasMore = page * PAGE_SIZE < total;

    // Handle refresh logic exposed to parent
    useImperativeHandle(ref, () => ({
      refresh: () => {
        refetch();
      },
      openNewTaskModal: () => {
        setEditingTask(null);
        setIsNewTaskModalOpen(true);
      },
    }));

    // Other handlers
    const handleTaskClick = useCallback(
      (task: Task) => {
        if (task.projectId) {
          router.push(`/projects/${task.projectId}/tasks/${task.id}`);
        }
      },
      [router],
    );

    const handleEditTask = useCallback((task: Task) => {
      setEditingTask(task);
      setIsNewTaskModalOpen(true);
      setOpenMenuId(null);
    }, []);

    const handleDeleteTask = useCallback((task: Task) => {
      setTaskToDelete(task);
      setIsDeleteModalOpen(true);
      setOpenMenuId(null);
    }, []);

    const confirmDeleteTask = useCallback(() => {
      if (taskToDelete) {
        deleteTask(taskToDelete, {
          onSuccess: () => {
            setOpenMenuId(null);
            setIsDeleteModalOpen(false);
            setTaskToDelete(null);
            if (onTaskChange) {
              onTaskChange();
            }
          },
        });
      }
    }, [deleteTask, taskToDelete, onTaskChange]);

    const toggleMenu = useCallback((e: React.MouseEvent, taskId: string) => {
      e.stopPropagation();
      setOpenMenuId((prev) => (prev === taskId ? null : taskId));
    }, []);

    const handleClearSearch = useCallback(() => {
      setLocalSearchQuery("");
      setPage(1);
      searchInputRef.current?.focus();
    }, []);

    // Close menu when clicking outside
    useEffect(() => {
      const handleClickOutside = (event: MouseEvent) => {
        if (!openMenuId) {
          return;
        }

        // Handle text nodes (e.g. clicking text inside button)
        let target = event.target as Node;
        if (target.nodeType === Node.TEXT_NODE) {
          target = target.parentNode as Node;
        }

        const element = target as Element;

        // Safety check for .closest method
        if (!element || typeof element.closest !== "function") {
          return;
        }

        if (
          !element.closest(".task-menu-trigger") &&
          !element.closest(".task-menu-dropdown")
        ) {
          setOpenMenuId(null);
        }
      };
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }, [openMenuId]);

    // RENDER LOGIC
    if (isLoading) {
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
              <Card key={i} className="border-border bg-card">
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
      const errorMessage =
        typeof error === "string"
          ? error
          : ((error as Error)?.message ?? "Failed to load tasks.");

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
              <h2 className="text-3xl font-bold tracking-tight text-foreground">
                {title}
              </h2>
              <p className="mt-1 text-muted-foreground">{description}</p>
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button
                className="flex-1 sm:flex-none bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg shadow-primary/20"
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
        <div className="space-y-4 relative z-10">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search
                className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                ref={searchInputRef}
                id={searchId}
                name={`task-search-${searchId}`}
                type="search"
                role="searchbox"
                placeholder="Search tasks..."
                aria-label="Search tasks"
                autoComplete="off"
                aria-autocomplete="none"
                data-1p-ignore="true"
                data-lpignore="true"
                data-protonpass-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                value={localSearchQuery}
                onChange={(e) => setLocalSearchQuery(e.target.value)}
                className="pl-10 bg-background border-border text-foreground placeholder:text-muted-foreground h-10"
              />
              {localSearchQuery && (
                <button
                  onClick={handleClearSearch}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 p-1 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground transition-all duration-200"
                  title="Clear search"
                  aria-label="Clear search"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
            <CustomSelect
              value={statusFilter === "all" ? "" : statusFilter}
              placeholder="All Status"
              onChange={(value: string) => {
                setStatusFilter(value);
              }}
              options={[
                ...(statusFilter !== "all"
                  ? [{ value: "all", label: "All Status" }]
                  : []),
                { value: "todo", label: "To Do" },
                { value: "in_progress", label: "In Progress" },
                { value: "in_review", label: "In Review" },
                { value: "done", label: "Done" },
                { value: "cancelled", label: "Cancelled" },
              ]}
              className="w-full sm:w-[180px] h-10"
              triggerClassName="h-10"
            />
          </div>
        </div>

        {/* Content */}
        <div className="space-y-4">
          {paginatedTasks.length > 0 ? (
            paginatedTasks.map((task) => (
              <TaskItem
                key={task.id}
                task={task}
                showProjectName={showProjectName}
                isOpen={openMenuId === task.id}
                isDeleting={isDeleting && taskToDelete?.id === task.id}
                onToggleMenu={toggleMenu}
                onEdit={handleEditTask}
                onDelete={handleDeleteTask}
                onClick={handleTaskClick}
              />
            ))
          ) : (
            <div className="text-center py-20 bg-card/10 rounded-2xl border border-dashed border-border animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="relative inline-flex items-center justify-center mb-4 h-16 w-16 rounded-full bg-muted/50">
                <Search className="h-8 w-8 text-primary/60" />
              </div>
              <h3 className="text-xl font-semibold text-foreground mb-2">No tasks found</h3>
              <p className="text-muted-foreground max-w-xs mx-auto mb-6">
                We couldn't find any tasks matching your current search or filters.
              </p>
              {(localSearchQuery || statusFilter !== "all") && (
                <Button 
                  variant="outline" 
                  onClick={() => {
                    handleClearSearch();
                    setStatusFilter("all");
                  }}
                  className="rounded-full px-6 hover:bg-primary/5 hover:text-primary hover:border-primary/30 transition-all duration-300"
                >
                  Clear all filters
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Pagination Controls */}
        {paginatedTasks.length > 0 && (
          <div className="flex justify-between items-center mt-8">
            <div className="text-sm text-muted-foreground">
              Showing {(page - 1) * PAGE_SIZE + 1} to{" "}
              {Math.min(page * PAGE_SIZE, total)} of {total}{" "}
              tasks
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="flex items-center gap-2"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <div className="flex items-center px-4 py-1 bg-muted rounded-md border border-border shadow-sm">
                <span className="text-sm font-bold text-foreground tracking-wide">
                  Page {page}
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={!hasMore}
                className="flex items-center gap-2"
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
            refetch();
            // Invalidate all task queries to ensure consistency across views (project vs global)
            queryClient.invalidateQueries({ queryKey: ["tasks"] });
            setIsNewTaskModalOpen(false);
            setEditingTask(null);
            if (onTaskChange) {
              onTaskChange();
            }
          }}
          defaultProjectId={projectId}
          task={editingTask}
        />

        <DeleteTaskModal
          isOpen={isDeleteModalOpen}
          onClose={() => {
            setIsDeleteModalOpen(false);
            setTaskToDelete(null);
          }}
          onConfirm={confirmDeleteTask}
          task={taskToDelete}
          isDeleting={isDeleting}
        />
      </div>
    );
  },
);

TaskList.displayName = "TaskList";
