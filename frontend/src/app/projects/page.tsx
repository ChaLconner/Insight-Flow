"use client";

import { useState, useMemo, useRef, useCallback, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ProjectStatus } from "@/types";
import type { CreateProjectRequest, UpdateProjectRequest, Project } from "@/types";
import dynamic from 'next/dynamic';
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { useAuthStore } from "@/stores/auth-store";
import { TaskList, type TaskListRef } from "@/components/tasks/TaskList";
import { ProjectFilters } from "@/components/projects/ProjectFilters";
import { useProjects, useCreateProject, useUpdateProject, useArchiveProject } from "@/hooks/use-projects";
import { ProjectHeader } from "@/components/projects/ProjectHeader";
import { ProjectGrid } from "@/components/projects/ProjectGrid";
import { useDebounce } from "@/hooks/use-debounce";

const ProjectModal = dynamic(() => import('@/components/modals/ProjectModal').then(mod => mod.ProjectModal), {
  loading: () => null,
  ssr: false
});

export default function ProjectsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated } = useAuthStore();

  // URL State
  const activeTab: 'projects' | 'tasks' = searchParams.get('tab') === 'tasks' ? 'tasks' : 'projects';

  // Local State
  const [searchQuery, setSearchQuery] = useState(searchParams.get("search") ?? "");
  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  const [statusFilter, setStatusFilter] = useState<ProjectStatus | "all">("all");
  const [sortBy, setSortBy] = useState<"newest" | "oldest" | "name">("newest");
  const [showFilters, setShowFilters] = useState(false);

  // Modal State
  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");

  const taskListRef = useRef<TaskListRef>(null);

  // Hooks
  const {
    data: projects = [],
    isLoading,
    isError,
    error,
    refetch,
    isRefetching
  } = useProjects({ enabled: activeTab === 'projects' });

  const createProjectMutation = useCreateProject();
  const updateProjectMutation = useUpdateProject();
  const archiveProjectMutation = useArchiveProject();

  // Handlers
  const handleTabChange = useCallback((tab: 'projects' | 'tasks') => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('tab', tab);
    router.push(`/projects?${params.toString()}`);
  }, [router, searchParams]);

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

  const handleArchiveProject = useCallback(async (project: Project) => {
    if (!confirm("Are you sure you want to archive this project?")) { return; }
    archiveProjectMutation.mutate(project);
  }, [archiveProjectMutation]);

  const handleProjectSubmit = useCallback(async (data: CreateProjectRequest | UpdateProjectRequest) => {
    try {
      if (modalMode === "create") {
        await createProjectMutation.mutateAsync(data as CreateProjectRequest);
      } else if (editingProject) {
        await updateProjectMutation.mutateAsync({
          id: editingProject.id,
          data: data as UpdateProjectRequest
        });
      }
      setIsProjectModalOpen(false);
      setEditingProject(null);
    } catch (err) {
      console.error(err);
    }
  }, [modalMode, editingProject, createProjectMutation, updateProjectMutation]);

  // Derived Data
  const filteredProjects = useMemo(() => {
    if (activeTab !== 'projects') return [];

    return projects
      .filter(project => {
        const matchesSearch = project.name.toLowerCase().includes(debouncedSearchQuery.toLowerCase()) ||
          project.description?.toLowerCase().includes(debouncedSearchQuery.toLowerCase());
        const matchesStatus = statusFilter === "all" || project.status === statusFilter;
        return matchesSearch && matchesStatus;
      })
      .sort((a, b) => {
        if (sortBy === "name") {
          return a.name.localeCompare(b.name);
        } else if (sortBy === "oldest") {
          return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
        } else {
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
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
    setPage(p => p + 1);
  }, []);

  // Reset pagination when filters change
  useEffect(() => {
    setPage(1);
  }, [searchQuery, statusFilter, sortBy]);

  if (!isAuthenticated) {
    return <ProtectedLayout><div></div></ProtectedLayout>;
  }

  // Error State
  if (isError) {
    return (
      <ProtectedLayout>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="text-red-400 text-center">
            <p className="text-lg font-medium">
              {(error as Error)?.message || 'Failed to load projects'}
            </p>
            <Button
              onClick={() => refetch()}
              className="mt-2"
              variant="outline"
            >
              Retry
            </Button>
          </div>
        </div>
      </ProtectedLayout>
    );
  }

  // Loading State (Initial)
  if (isLoading && activeTab === "projects") {
    return (
      <ProtectedLayout>
        <div className="space-y-8">
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
          <div className="flex flex-col sm:flex-row gap-4">
            <Skeleton className="h-10 flex-1" />
            <div className="flex gap-2">
              <Skeleton className="h-10 w-32" />
              <Skeleton className="h-10 w-32" />
            </div>
          </div>
          <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {[...Array(6)].map((_, i) => (
              <Skeleton key={i} className="h-[300px] w-full rounded-xl" />
            ))}
          </div>
        </div>
      </ProtectedLayout>
    );
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

        {activeTab === "projects" ? (
          <>
            <ProjectFilters
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              statusFilter={statusFilter}
              onStatusFilterChange={setStatusFilter}
              showFilters={showFilters}
              onToggleFilters={() => setShowFilters(!showFilters)}
              sortBy={sortBy}
              onSortChange={setSortBy}
              onClear={() => {
                setSearchQuery("");
                setStatusFilter("all");
                setSortBy("newest");
              }}
            />

            <ProjectGrid
              projects={paginatedProjects}
              isLoading={isLoading}
              onEdit={handleEditProject}
              onArchive={handleArchiveProject}
              hasFilters={!!(searchQuery || statusFilter !== "all")}
              onCreateProject={handleCreateProject}
            />
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
    </ProtectedLayout >
  );
}