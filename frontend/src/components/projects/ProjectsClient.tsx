"use client";

import { useState, useRef, useCallback, useEffect, Suspense } from "react";
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
import {
  ProjectGridSkeleton,
  ProjectsPageSkeletonContent,
} from "@/components/projects/ProjectsPageSkeleton";
import { useFavoriteIds, useToggleFavorite } from "@/hooks/use-favorites";
import {
  blurEditableTargetOnEscape,
  useDocumentKeyDown,
} from "@/hooks/use-keyboard-shortcuts";

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

function ProjectsPageSkeleton() {
  return (
    <ProtectedLayout>
      <ProjectsPageSkeletonContent />
    </ProtectedLayout>
  );
}

export function ProjectsClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuthStore();

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
  const [page, setPage] = useState(1);
  const pageSize = 12;

  // Data fetching with server-side filtering/sorting. Load More increases the
  // bounded limit instead of fetching a fixed 100 rows and filtering locally.
  const {
    data: projects = [],
    isLoading,
    isRefetching,
    refetch,
  } = useProjects({
    page: 1,
    pageSize: page * pageSize + 1,
    search: debouncedSearchQuery,
    status: statusFilter,
    sortBy,
    enabled: activeTab === "projects",
  });


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

  const handleKeyboardShortcut = useCallback((event: KeyboardEvent) => {
    if (blurEditableTargetOnEscape(event)) {
      return;
    }

    if (event.key === "/") {
      event.preventDefault();
      searchInputRef.current?.focus();
    }
  }, []);
  useDocumentKeyDown(handleKeyboardShortcut);

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

  const visibleProjectLimit = page * pageSize;
  const visibleProjects = projects.slice(0, visibleProjectLimit);
  const hasMoreProjects = projects.length > visibleProjectLimit;

  const handleLoadMore = useCallback(() => {
    setPage((p) => p + 1);
  }, []);

  // Reset pagination when filters change
  useEffect(() => {
    setPage(1);
  }, [debouncedSearchQuery, statusFilter, sortBy]);

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
                projects={visibleProjects}
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
