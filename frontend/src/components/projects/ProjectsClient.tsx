"use client";

import { useState, useMemo, useRef, useCallback, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import type { ProjectStatus } from "@/types";
import type {
  CreateProjectRequest,
  UpdateProjectRequest,
  Project,
} from "@/types";
import dynamic from "next/dynamic";
import { useAuthStore } from "@/stores/auth-store";
import { TaskList, type TaskListRef } from "@/components/tasks/TaskList";
import { ProjectFilters } from "@/components/projects/ProjectFilters";
import {
  useProjects,
  useCreateProject,
  useUpdateProject,
  useArchiveProject,
} from "@/hooks/use-projects";
import { ProjectHeader } from "@/components/projects/ProjectHeader";
import { useDebounce } from "@/hooks/use-debounce";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { Loader2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useFavoriteIds, useToggleFavorite } from "@/hooks/use-favorites";

// Lazy load heavy components
const ProjectModal = dynamic(
  () =>
    import("@/components/modals/ProjectModal").then((mod) => mod.ProjectModal),
  {
    loading: () => null,
    ssr: false,
  }
);

const ProjectGrid = dynamic(
  () =>
    import("@/components/projects/ProjectGrid").then((mod) => mod.ProjectGrid),
  {
    loading: () => <ProjectGridSkeleton />,
    ssr: false,
  }
);

// Skeleton for ProjectGrid while loading
function ProjectGridSkeleton() {
  return (
    <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <Skeleton key={i} className="h-[300px] w-full rounded-xl" />
      ))}
    </div>
  );
}

// Loading skeleton for entire page
function ProjectsPageSkeleton() {
  return (
    <ProtectedLayout>
      <div className="space-y-8">
        {/* Header Skeleton */}
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

        {/* Filters Skeleton */}
        <div className="flex flex-col sm:flex-row gap-4">
          <Skeleton className="h-10 flex-1" />
          <div className="flex gap-2">
            <Skeleton className="h-10 w-32" />
            <Skeleton className="h-10 w-32" />
          </div>
        </div>

        {/* Grid Skeleton */}
        <ProjectGridSkeleton />
      </div>
    </ProtectedLayout>
  );
}

export function ProjectsClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuthStore();

  // Data fetching with React Query (like Dashboard/Analytics)
  const { data: projects = [], isLoading, isRefetching, refetch } = useProjects();

  // URL State
  const activeTab: "projects" | "tasks" =
    searchParams.get("tab") === "tasks" ? "tasks" : "projects";

  // Local State
  const [searchQuery, setSearchQuery] = useState(
    searchParams.get("search") ?? ""
  );
  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  const [statusFilter, setStatusFilter] = useState<ProjectStatus | "all">(
    "all"
  );
  const [sortBy, setSortBy] = useState<"newest" | "oldest" | "name">("newest");


  // Modal State
  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");

  // Favorites State (from API)
  const { data: favoriteIds = new Set<string>() } = useFavoriteIds();
  const toggleFavoriteMutation = useToggleFavorite();

  const taskListRef = useRef<TaskListRef>(null);
  const actionProcessedRef = useRef(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        // Allow Escape to blur
        if (e.key === "Escape") {
          target.blur();
        }
        return;
      }

      if (e.key === "/") {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Handle action=create from Quick Actions
  useEffect(() => {
    if (actionProcessedRef.current) {
      return;
    }
    let hasCreateAction = searchParams.get("action") === "create";
    
    if (!hasCreateAction && typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      hasCreateAction = urlParams.get("action") === "create";
    }
    
    if (hasCreateAction) {
      actionProcessedRef.current = true;
      setModalMode("create");
      setEditingProject(null);
      setIsProjectModalOpen(true);
      const newUrl = window.location.pathname;
      router.replace(newUrl, { scroll: false });
    }
  }, [searchParams, router]);

  const createProjectMutation = useCreateProject();
  const updateProjectMutation = useUpdateProject();
  const archiveProjectMutation = useArchiveProject();

  // Handlers
  const handleTabChange = useCallback(
    (tab: "projects" | "tasks") => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("tab", tab);
      router.push(`/projects?${params.toString()}`);
    },
    [router, searchParams]
  );

  const handleRefresh = useCallback(() => {
    if (activeTab === "projects") {
      refetch();
    } else {
      taskListRef.current?.refresh();
    }
  }, [activeTab, refetch]);

  const handleCreateProject = useCallback(() => {
    setModalMode("create");
    setEditingProject(null);
    setIsProjectModalOpen(true);
  }, []);

  const handleEditProject = useCallback((project: Project) => {
    setModalMode("edit");
    setEditingProject(project);
    setIsProjectModalOpen(true);
  }, []);

  const handleArchiveProject = useCallback(
    async (project: Project) => {
      if (!confirm("Are you sure you want to archive this project?")) {
        return;
      }
      await archiveProjectMutation.mutateAsync(project);
    },
    [archiveProjectMutation]
  );

  const handleFavoriteProject = useCallback(
    (project: Project) => {
      toggleFavoriteMutation.mutate(project.id);
    },
    [toggleFavoriteMutation]
  );

  const handleProjectSubmit = useCallback(
    async (data: CreateProjectRequest | UpdateProjectRequest) => {
      try {
        if (modalMode === "create") {
          await createProjectMutation.mutateAsync(data as CreateProjectRequest);
        } else if (editingProject) {
          await updateProjectMutation.mutateAsync({
            id: editingProject.id,
            data: data as UpdateProjectRequest,
          });
        }
        setIsProjectModalOpen(false);
        setEditingProject(null);
      } catch (err) {
        console.error(err);
      }
    },
    [
      modalMode,
      editingProject,
      createProjectMutation,
      updateProjectMutation,
    ]
  );

  // Derived Data with memoization
  const filteredProjects = useMemo(() => {
    if (activeTab !== "projects") {
      return [];
    }

    return projects
      .filter((project) => {
        const matchesSearch =
          project.name
            .toLowerCase()
            .includes(debouncedSearchQuery.toLowerCase()) ||
          project.description
            ?.toLowerCase()
            .includes(debouncedSearchQuery.toLowerCase());
        const matchesStatus =
          statusFilter === "all" || project.status === statusFilter;
        return matchesSearch && matchesStatus;
      })
      .sort((a, b) => {
        if (sortBy === "name") {
          return a.name.localeCompare(b.name);
        } else if (sortBy === "oldest") {
          return (
            new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
          );
        } else {
          return (
            new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
          );
        }
      });
  }, [projects, debouncedSearchQuery, statusFilter, sortBy, activeTab]);

  // Client-side Pagination
  const [page, setPage] = useState(1);
  const pageSize = 12;
  const paginatedProjects = useMemo(() => {
    return filteredProjects.slice(0, page * pageSize);
  }, [filteredProjects, page]);

  const hasMoreProjects = paginatedProjects.length < filteredProjects.length;

  const handleLoadMore = useCallback(() => {
    setPage((p) => p + 1);
  }, []);

  // Reset pagination when filters change
  useEffect(() => {
    setPage(1);
  }, [searchQuery, statusFilter, sortBy]);

  // Loading state - show skeleton
  if (authLoading || (isLoading && projects.length === 0)) {
    return <ProjectsPageSkeleton />;
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <ProtectedLayout>
      <div className="space-y-8">
        <ProjectHeader
          activeTab={activeTab}
          onTabChange={handleTabChange}
          onRefresh={handleRefresh}
          onCreateProject={handleCreateProject}
          isRefetching={isRefetching}
        />

        {/* Background refetch indicator */}
        {isRefetching && projects.length > 0 && (
          <div className="flex items-center justify-center py-2">
            <div className="flex items-center gap-2 text-sm text-zinc-400 bg-white/5 px-4 py-2 rounded-full">
              <Loader2 className="w-4 h-4 animate-spin" />
              Updating...
            </div>
          </div>
        )}

        {activeTab === "projects" ? (
          <>
            <ProjectFilters
              ref={searchInputRef}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              statusFilter={statusFilter}
              onStatusFilterChange={setStatusFilter}
              sortBy={sortBy}
              onSortChange={setSortBy}
              onClear={() => {
                setSearchQuery("");
                setStatusFilter("all");
                setSortBy("newest");
              }}
            />

            <Suspense fallback={<ProjectGridSkeleton />}>
              <ProjectGrid
                projects={paginatedProjects}
                isLoading={isLoading}
                onEdit={handleEditProject}
                onArchive={handleArchiveProject}
                onFavorite={handleFavoriteProject}
                favoriteIds={favoriteIds}
                hasFilters={!!(searchQuery || statusFilter !== "all")}
                onCreateProject={handleCreateProject}
              />
            </Suspense>
            
            {hasMoreProjects && (
              <div className="mt-8 flex justify-center">
                <Button
                  variant="outline"
                  onClick={handleLoadMore}
                  className="w-full md:w-auto"
                >
                  Load More Projects
                </Button>
              </div>
            )}
          </>
        ) : (
          <div className="w-full min-h-[500px]">
            <TaskList
              ref={taskListRef}
              hideHeader={true}
              showProjectName={true}
            />
          </div>
        )}

        {/* Project Modal */}
        <ProjectModal
          isOpen={isProjectModalOpen}
          onClose={() => setIsProjectModalOpen(false)}
          project={editingProject}
          mode={modalMode}
          onSubmit={handleProjectSubmit}
        />
      </div>
    </ProtectedLayout>
  );
}
