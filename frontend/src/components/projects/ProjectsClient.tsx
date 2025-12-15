"use client";

import { useState, useMemo, useRef, useCallback, useEffect } from "react";
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
  useCreateProject,
  useUpdateProject,
  useArchiveProject,
} from "@/hooks/use-projects";
import { ProjectHeader } from "@/components/projects/ProjectHeader";
import { ProjectGrid } from "@/components/projects/ProjectGrid";
import { useDebounce } from "@/hooks/use-debounce";

const ProjectModal = dynamic(
  () =>
    import("@/components/modals/ProjectModal").then((mod) => mod.ProjectModal),
  {
    loading: () => null,
    ssr: false,
  },
);

interface ProjectsClientProps {
  initialProjects: Project[];
}

export function ProjectsClient({ initialProjects }: ProjectsClientProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated } = useAuthStore();

  // URL State
  const activeTab: "projects" | "tasks" =
    searchParams.get("tab") === "tasks" ? "tasks" : "projects";

  // Local State
  const [searchQuery, setSearchQuery] = useState(
    searchParams.get("search") ?? "",
  );
  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  const [statusFilter, setStatusFilter] = useState<ProjectStatus | "all">(
    "all",
  );
  const [sortBy, setSortBy] = useState<"newest" | "oldest" | "name">("newest");
  const [showFilters, setShowFilters] = useState(false);

  // Modal State
  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");

  const taskListRef = useRef<TaskListRef>(null);

  const projects = initialProjects;
  const isRefetching = false;

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
    [router, searchParams],
  );

  const handleRefresh = useCallback(() => {
    if (activeTab === "projects") {
      router.refresh();
    } else {
      taskListRef.current?.refresh();
    }
  }, [activeTab, router]);

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
      router.refresh();
    },
    [archiveProjectMutation, router],
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
        router.refresh();
      } catch (err) {
        console.error(err);
      }
    },
    [
      modalMode,
      editingProject,
      createProjectMutation,
      updateProjectMutation,
      router,
    ],
  );

  // Derived Data
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

  if (!isAuthenticated) {
    return null;
  }

  return (
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
            isLoading={false} // Data is already here
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
  );
}
