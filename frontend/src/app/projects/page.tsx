"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Search,
  Filter,
  Plus,
  MoreHorizontal,
  Settings,
  Users,
  Calendar,
  TrendingUp,
  Archive,
  Trash2,
  Eye,
  Edit,
  RefreshCw,
  ChevronDown,
  X,
  LayoutGrid,
  ListTodo
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Skeleton } from "@/components/ui/skeleton";
import { ProjectStatus } from "@/types";
import type { CreateProjectRequest, UpdateProjectRequest, Project } from "@/types";
import dynamic from 'next/dynamic';

const ProjectModal = dynamic(() => import('@/components/modals/ProjectModal').then(mod => mod.ProjectModal), {
  loading: () => null,
  ssr: false
});
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { CustomSelect } from "@/components/ui/custom-select";
import { useAuthStore } from "@/stores/auth-store";
import { projectsApi } from "@/lib/api-endpoints";
import type { TaskListRef } from "@/components/tasks/TaskList";
import { TaskList } from "@/components/tasks/TaskList";
import { NewTaskModal } from "@/components/tasks/NewTaskModal";
import { getAvatarUrl } from "@/lib/utils";


// Colors for projects
const PROJECT_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const searchParams = useSearchParams();
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState(searchParams.get("search") ?? "");
  const [statusFilter, setStatusFilter] = useState<ProjectStatus | "all">("all");
  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [isNewTaskModalOpen, setIsNewTaskModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");

  const [refreshing, setRefreshing] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [sortBy, setSortBy] = useState<"newest" | "oldest" | "name">("newest");
  const [activeTab, setActiveTab] = useState<'projects' | 'tasks'>(
    (searchParams.get('tab') as 'projects' | 'tasks') ?? 'projects'
  );
  const taskListRef = useRef<TaskListRef>(null);

  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  const isLoading = useAuthStore(state => state.isLoading);
  const user = useAuthStore(state => state.user);
  const logout = useAuthStore(state => state.logout);

  const [dataFetched, setDataFetched] = useState(false);

  // Use refs to prevent duplicate calls
  const isLoadingRef = useRef(false);
  const lastLoadTime = useRef<number>(0);



  const handleTabChange = (tab: 'projects' | 'tasks') => {
    setActiveTab(tab);
    const params = new URLSearchParams(searchParams.toString());
    params.set('tab', tab);
    router.push(`/projects?${params.toString()}`);
  };

  // Memoized loadProjects function
  const loadProjects = useCallback(async (forceRefresh = false) => {
    if (!isAuthenticated) return;

    try {
      if (forceRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      // Use API endpoint
      const data = await projectsApi.getProjects(0, 100, false);

      // Convert backend response to frontend format with enhanced error handling
      const formattedProjects = data.map((project: any, index: number) => {


        // Find owner from member summaries with fallback
        const ownerMember = project.memberSummaries?.find((m: any) => m.role === 'owner');

        // Safely extract owner name
        const getOwnerName = () => {
          if (ownerMember?.name) {
            return ownerMember.name;
          }
          if (project.ownerName) {
            return project.ownerName;
          }
          if (user?.name) {
            return user.name;
          }
          return "Unknown User";
        };

        const ownerName = getOwnerName();

        return {
          id: project.id ?? `project-${index}`,
          name: project.name ?? "Unnamed Project",
          description: project.description ?? "",
          color: project.color ?? PROJECT_COLORS[index % PROJECT_COLORS.length],
          status: project.isActive !== false ? ProjectStatus.ACTIVE : ProjectStatus.ARCHIVED,
          ownerId: project.ownerId ?? user?.id ?? "unknown",
          owner: {
            id: project.ownerId ?? user?.id ?? "unknown",
            email: ownerMember?.email ?? user?.email ?? "unknown@company.com",
            username: ownerMember?.name?.toLowerCase().replace(/\s+/g, '') ??
              user?.username ??
              ownerName.toLowerCase().replace(/\s+/g, '') ??
              "unknownuser",
            firstName: ownerMember?.name?.split(' ')[0] ??
              ownerName.split(' ')[0] ??
              user?.firstName ??
              "Unknown",
            lastName: ownerMember?.name?.split(' ').slice(1).join(' ') ??
              ownerName.split(' ').slice(1).join(' ') ??
              user?.lastName ??
              "User",
            role: "admin" as any, // Owner is always admin/owner
            isActive: true,
            emailVerified: true,
            createdAt: project.createdAt ?? new Date().toISOString(),
            updatedAt: project.updatedAt ?? new Date().toISOString(),
            avatar: getAvatarUrl(ownerMember?.avatar ?? user?.avatar)
          },
          members: (project.memberSummaries ?? project.members ?? []).map((m: any) => ({
            id: m.id ?? `member-${m.userId}-${index}`,
            userId: m.userId ?? m.id ?? "unknown",
            projectId: project.id ?? `project-${index}`,
            role: m.role ?? "member",
            joinedAt: m.joinedAt ?? new Date().toISOString(),
            user: {
              id: m.userId ?? m.id ?? "unknown",
              email: m.email ?? "unknown@company.com",
              name: m.name ?? ownerName,
              avatar: getAvatarUrl(m.avatar),
              role: m.role ?? "member",
              isActive: m.isActive !== false,
              emailVerified: m.emailVerified !== false,
              createdAt: m.createdAt ?? new Date().toISOString(),
              updatedAt: m.updatedAt ?? new Date().toISOString()
            }
          })),
          stats: {
            totalTasks: Number(project.taskCount ?? project.task_count ?? project.totalTasks ?? 0),
            completedTasks: Number(project.completedTasks ?? project.completed_tasks ?? 0),
            inProgressTasks: (Number(project.taskCount ?? project.task_count ?? 0)) - (Number(project.completedTasks ?? project.completed_tasks ?? 0)),
            overdueTasks: Number(project.overdueTasks ?? project.overdue_tasks ?? 0),
            teamMembers: Number(project.memberCount ?? project.member_count ?? (project.memberSummaries ?? project.member_summaries ?? []).length ?? 1),
            recentActivity: Number(project.recentActivity ?? project.recent_activity ?? 0)
          },
          settings: {
            allowPublicAccess: project.settings?.allowPublicAccess ?? false,
            requireApproval: project.settings?.requireApproval !== false,
            defaultTaskVisibility: project.settings?.defaultTaskVisibility ?? "team" as "team" | "private" | "public",
            notificationSettings: {
              taskAssigned: project.settings?.notificationSettings?.taskAssigned !== false,
              statusChanged: project.settings?.notificationSettings?.statusChanged !== false,
              deadlineApproaching: project.settings?.notificationSettings?.deadlineApproaching !== false,
              commentAdded: project.settings?.notificationSettings?.commentAdded !== false
            }
          },
          createdAt: project.createdAt ?? new Date().toISOString(),
          updatedAt: project.updatedAt ?? new Date().toISOString(),
          taskCount: Number(project.taskCount ?? project.task_count ?? 0),
          completedTasks: Number(project.completedTasks ?? project.completed_tasks ?? 0),
          memberCount: Number(project.memberCount ?? project.member_count ?? (project.memberSummaries ?? project.member_summaries ?? []).length ?? 1)
        };
      });

      setProjects(formattedProjects);
      setDataFetched(true);
    } catch (err: any) {
      console.error('❌ ProjectsPage: Error loading projects:', err);

      // Enhanced error handling with token refresh logic
      let errorMessage = 'Failed to load projects';
      if (err.response?.status === 401) {
        errorMessage = 'Authentication expired. Please log in again.';

        // Clear auth state and redirect to login
        const { logout } = useAuthStore.getState();
        logout();

        // Redirect to login page after a short delay
        setTimeout(() => {
          window.location.href = '/auth/login';
        }, 1000);

      } else if (err.response?.status === 403) {
        errorMessage = 'Access denied. You do not have permission to view projects.';
      } else if (err.response?.status >= 500) {
        errorMessage = 'Server error. Please try again later.';
      } else if (err.code === 'NETWORK_ERROR' || err.message?.includes('Network Error')) {
        errorMessage = 'Network error. Please check your connection.';
      } else if (err.message) {
        errorMessage = err.message;
      } else if (typeof err === 'string') {
        errorMessage = err;
      }

      setError(errorMessage);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [isAuthenticated, dataFetched]);

  const createProject = async (projectData: CreateProjectRequest): Promise<Project> => {
    if (!isAuthenticated) { throw new Error('User not authenticated'); }

    const response = await projectsApi.createProject(projectData) as any;

    // Convert backend response to frontend format
    return {
      id: response.id,
      name: response.name,
      description: response.description,
      color: projectData.color ?? PROJECT_COLORS[0],
      status: ProjectStatus.ACTIVE,
      ownerId: response.ownerId,
      owner: {
        id: response.ownerId,
        email: user?.email ?? "current@company.com",
        username: user?.name?.toLowerCase().replace(/\s+/g, '') ?? "currentuser",
        firstName: user?.name?.split(' ')[0] ?? "Current",
        lastName: user?.name?.split(' ').slice(1).join(' ') ?? "User",
        role: "admin" as any,
        isActive: true,
        emailVerified: true,
        createdAt: response.createdAt,
        updatedAt: response.updatedAt,
        avatar: getAvatarUrl(user?.avatar)
      },
      members: (response.memberSummaries ?? []).map((m: any) => ({
        id: m.id,
        userId: m.userId,
        projectId: response.id,
        role: m.role,
        joinedAt: new Date().toISOString(),
        user: {
          id: m.userId,
          email: m.email,
          name: m.name,
          avatar: getAvatarUrl(m.avatar),
          role: "member",
          isActive: true,
          emailVerified: true,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        }
      })),
      stats: {
        totalTasks: 0,
        completedTasks: 0,
        inProgressTasks: 0,
        overdueTasks: 0,
        teamMembers: response.memberCount ?? 1,
        recentActivity: 0
      },
      settings: {
        allowPublicAccess: false,
        requireApproval: true,
        defaultTaskVisibility: "team" as "team" | "private" | "public",
        notificationSettings: {
          taskAssigned: true,
          statusChanged: true,
          deadlineApproaching: true,
          commentAdded: true
        }
      },
      createdAt: response.createdAt,
      updatedAt: response.updatedAt
    };
  };

  // Initial load
  useEffect(() => {
    if (isAuthenticated && !dataFetched) {
      loadProjects();
    }
  }, [isAuthenticated, dataFetched, loadProjects]);

  // Fallback timeout to prevent infinite loading
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (loading && !dataFetched) {
        console.warn('⚠️ ProjectsPage: Loading timeout');
        setError('Loading timed out. Please check your connection and refresh.');
        setLoading(false);
      }
    }, 45000); // Increased to 45 second timeout

    return () => clearTimeout(timeout);
  }, [loading, dataFetched, isAuthenticated]);

  const filteredProjects = projects
    .filter(project => {
      const matchesSearch = project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        project.description?.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === "all" || project.status === statusFilter;
      return matchesSearch && matchesStatus;
    })
    .sort((a, b) => {
      if (sortBy === "name") {
        return a.name.localeCompare(b.name);
      } else if (sortBy === "oldest") {
        return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
      } else {
        // newest
        return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
      }
    });

  const getStatusBadge = (status: ProjectStatus) => {
    const statusConfig = {
      [ProjectStatus.ACTIVE]: { label: "Active", color: "bg-emerald-500/20 text-emerald-400" },
      [ProjectStatus.ARCHIVED]: { label: "Archived", color: "bg-zinc-500/20 text-zinc-400" },
      [ProjectStatus.SUSPENDED]: { label: "Suspended", color: "bg-red-500/20 text-red-400" }
    };

    const config = statusConfig[status];
    return (
      <Badge className={config.color}>
        {config.label}
      </Badge>
    );
  };

  const getProgressPercentage = (stats: Project["stats"]) => {
    if (stats.totalTasks === 0) { return 0; }
    return Math.round((stats.completedTasks / stats.totalTasks) * 100);
  };

  const handleCreateProject = () => {
    setModalMode("create");
    setEditingProject(null);
    setIsProjectModalOpen(true);
  };

  const handleEditProject = (project: Project) => {
    setModalMode("edit");
    setEditingProject(project);
    setIsProjectModalOpen(true);
  };

  const handleProjectSubmit = async (
    data: CreateProjectRequest | UpdateProjectRequest
  ) => {
    if (!isAuthenticated) { return; }

    try {
      // Prepare data for API
      const apiData = { ...data } as any;

      // Map memberIds to members for backend
      if (apiData.memberIds && Array.isArray(apiData.memberIds)) {
        apiData.members = apiData.memberIds.map((userId: string) => ({
          userId,
          role: 'member'
        }));
        delete apiData.memberIds;
      }

      if (modalMode === "create") {
        const newProject = await createProject(apiData as CreateProjectRequest);
        setProjects((prev) => [...prev, newProject]);
      } else if (editingProject) {
        // Map status to is_active for backend
        if (apiData.status) {
          apiData.is_active = apiData.status === ProjectStatus.ACTIVE;
          delete apiData.status;
        }

        await projectsApi.updateProject(editingProject.id, apiData as UpdateProjectRequest);
        // Refresh projects to get updated data
        loadProjects(true);
      }
      setIsProjectModalOpen(false);
      setEditingProject(null);
      setError(null); // Clear any previous errors on success
    } catch (error) {
      console.error("Error saving project:", error);
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Failed to save project. Please try again.";
      setError(errorMessage);
    }
  };

  const handleRefresh = () => {
    if (activeTab === "projects") {
      loadProjects(true); // Force refresh
    } else {
      taskListRef.current?.refresh();
    }
  };

  const handleArchiveProject = async (project: Project) => {
    if (!isAuthenticated) { return; }
    if (!confirm("Are you sure you want to archive this project?")) { return; }

    try {
      // Optimistic update
      setProjects((prev) =>
        prev.map((p) =>
          p.id === project.id ? { ...p, status: ProjectStatus.ARCHIVED } : p
        )
      );

      // API call - assuming the backend accepts is_active or status update
      // We cast to any here because we're sending a partial update that might not perfectly match the strict type yet
      await projectsApi.updateProject(project.id, { is_active: false } as any);
    } catch (error) {
      console.error("Failed to archive project:", error);
      // Revert on error
      loadProjects(true);
    }
  };

  // Enhanced token validation checks removed as we use cookies


  if (loading && !refreshing) {
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

          {/* Search and Filter Skeleton */}
          <div className="flex flex-col sm:flex-row gap-4">
            <Skeleton className="h-10 flex-1" />
            <div className="flex gap-2">
              <Skeleton className="h-10 w-32" />
              <Skeleton className="h-10 w-32" />
            </div>
          </div>

          {/* Projects Grid Skeleton */}
          <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {[...Array(6)].map((_, i) => (
              <Card key={i} className="border-white/10 bg-white/5 backdrop-blur-sm">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <Skeleton className="h-10 w-10 rounded-lg" />
                      <div className="space-y-2">
                        <Skeleton className="h-5 w-32" />
                        <Skeleton className="h-3 w-24" />
                      </div>
                    </div>
                    <Skeleton className="h-6 w-16 rounded-full" />
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Skeleton className="h-3 w-full" />
                    <Skeleton className="h-3 w-2/3" />
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <Skeleton className="h-3 w-12" />
                      <Skeleton className="h-3 w-8" />
                    </div>
                    <Skeleton className="h-2 w-full rounded-full" />
                  </div>
                  <div className="grid grid-cols-3 gap-4 pt-2">
                    {[...Array(3)].map((_, j) => (
                      <div key={j} className="text-center space-y-1">
                        <Skeleton className="h-4 w-4 mx-auto" />
                        <Skeleton className="h-5 w-8 mx-auto" />
                        <Skeleton className="h-3 w-10 mx-auto" />
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-2 pt-2">
                    <Skeleton className="h-8 flex-1" />
                    <Skeleton className="h-8 w-8" />
                    <Skeleton className="h-8 w-8" />
                    <Skeleton className="h-8 w-8" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </ProtectedLayout>
    );
  }

  // Handle missing authentication or error state
  if (!isAuthenticated || error) {
    return (
      <ProtectedLayout>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="text-red-400 text-center">
            <p className="text-lg font-medium">
              {!isAuthenticated ? 'Authentication required. Please log in again.' : error}
            </p>
            <button
              onClick={() => !isAuthenticated ? router.push('/auth/login') : handleRefresh()}
              className="mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
            >
              {!isAuthenticated ? 'Go to Login' : 'Retry'}
            </button>
          </div>
        </div>
      </ProtectedLayout>
    );
  }

  return (
    <ProtectedLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-white">
              {activeTab === "projects" ? "Projects" : "My Tasks"}
            </h2>
            <p className="mt-1 text-zinc-400">
              {activeTab === "projects"
                ? "Manage and organize your projects in one place."
                : "Manage and track all your tasks across projects."}
            </p>
          </div>
          <div className="flex gap-2 w-full sm:w-auto">
            <Button
              onClick={handleRefresh}
              variant="ghost"
              className="flex-1 sm:flex-none glass border border-white/10 text-white hover:bg-white/10 hover:text-white"
              disabled={refreshing}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            {activeTab === "projects" ? (
              <Button
                onClick={handleCreateProject}
                className="flex-1 sm:flex-none bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                <Plus className="h-4 w-4 mr-2" />
                New Project
              </Button>
            ) : (
              <Button
                className="flex-1 sm:flex-none bg-indigo-600 hover:bg-indigo-500 text-white"
                onClick={() => setIsNewTaskModalOpen(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                New Task
              </Button>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex space-x-1 rounded-xl bg-white/5 p-1 w-fit">
          <button
            onClick={() => handleTabChange("projects")}
            className={`
              flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200
              ${activeTab === "projects"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                : "text-zinc-400 hover:text-white hover:bg-white/5"
              }
            `}
          >
            <LayoutGrid className="h-4 w-4" />
            Projects
          </button>
          <button
            onClick={() => handleTabChange("tasks")}
            className={`
              flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200
              ${activeTab === "tasks"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                : "text-zinc-400 hover:text-white hover:bg-white/5"
              }
            `}
          >
            <ListTodo className="h-4 w-4" />
            My Tasks
          </button>
        </div>

        {activeTab === "projects" ? (
          <>
            {/* Search and Filter */}
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" aria-hidden="true" />
                <Input
                  placeholder="Search projects..."
                  aria-label="Search projects"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-zinc-400"
                />
              </div>
              <div className="flex flex-col sm:flex-row gap-2">
                <CustomSelect
                  value={statusFilter}
                  onChange={(value) =>
                    setStatusFilter(value as ProjectStatus | "all")
                  }
                  options={[
                    { value: "all", label: "All Status" },
                    { value: ProjectStatus.ACTIVE, label: "Active" },
                    { value: ProjectStatus.ARCHIVED, label: "Archived" },
                    { value: ProjectStatus.SUSPENDED, label: "Suspended" },
                  ]}
                  className="w-full sm:w-[140px]"
                />
                <Button
                  variant="ghost"
                  className={`glass border border-white/10 text-white hover:bg-white/10 hover:text-white ${showFilters ? "bg-white/10 ring-1 ring-indigo-500/50" : ""
                    }`}
                  onClick={() => setShowFilters(!showFilters)}
                >
                  <ChevronDown
                    className={`h-4 w-4 mr-2 transition-transform ${showFilters ? "rotate-180" : ""
                      }`}
                  />
                  More Filters
                </Button>
                {(searchQuery || statusFilter !== "all" || sortBy !== "newest") && (
                  <Button
                    variant="ghost"
                    onClick={() => {
                      setSearchQuery("");
                      setStatusFilter("all");
                      setSortBy("newest");
                    }}
                    className="text-zinc-400 hover:text-white"
                  >
                    <X className="h-4 w-4 mr-2" />
                    Clear
                  </Button>
                )}
              </div>
            </div>

            {/* Extended Filters Panel */}
            <AnimatePresence>
              {showFilters && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-4 mb-6">
                    <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
                      <div className="space-y-1.5 flex-1">
                        <label className="text-xs font-medium text-zinc-400">Sort By</label>
                        <div className="flex gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSortBy("newest")}
                            className={`text-xs ${sortBy === "newest"
                              ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/30"
                              : "text-zinc-400 hover:text-white"
                              }`}
                          >
                            Newest
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSortBy("oldest")}
                            className={`text-xs ${sortBy === "oldest"
                              ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/30"
                              : "text-zinc-400 hover:text-white"
                              }`}
                          >
                            Oldest
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSortBy("name")}
                            className={`text-xs ${sortBy === "name"
                              ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/30"
                              : "text-zinc-400 hover:text-white"
                              }`}
                          >
                            Name
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Refresh indicator */}
            {refreshing && (
              <div className="flex items-center justify-center py-2">
                <div className="text-zinc-400 text-sm flex items-center">
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Refreshing projects...
                </div>
              </div>
            )}

            {/* Projects Grid */}
            <motion.div
              className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
              initial="hidden"
              animate="visible"
              variants={{
                hidden: { opacity: 0 },
                visible: {
                  opacity: 1,
                  transition: {
                    staggerChildren: 0.1,
                  },
                },
              }}
            >
              <AnimatePresence mode="popLayout">
                {filteredProjects.map((project) => (
                  <motion.div
                    key={project.id}
                    layout
                    variants={{
                      hidden: { opacity: 0, y: 20 },
                      visible: { opacity: 1, y: 0 },
                    }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    whileHover={{ y: -5, transition: { duration: 0.2 } }}
                    className="h-full"
                  >
                    <Card className="h-full border-white/10 bg-white/5 backdrop-blur-sm hover:bg-white/10 transition-colors group flex flex-col">
                      <CardHeader className="pb-3">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex items-center gap-3 flex-1 min-w-0">
                            <div
                              className="h-10 w-10 rounded-lg flex items-center justify-center shadow-lg transition-transform group-hover:scale-110 duration-300"
                              style={{ backgroundColor: project.color }}
                            >
                              <span className="font-bold text-white text-sm">
                                {project.name && typeof project.name === "string"
                                  ? project.name[0]
                                  : ""}
                              </span>
                            </div>
                            <div className="min-w-0 flex-1">
                              <CardTitle className="text-white text-lg truncate group-hover:text-indigo-400 transition-colors">
                                {project.name}
                              </CardTitle>
                              <p className="text-sm text-zinc-400 mt-1">
                                by {project.owner.firstName} {project.owner.lastName}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-1">
                            {getStatusBadge(project.status)}
                          </div>
                        </div>
                      </CardHeader>

                      <CardContent className="space-y-4 flex-1 flex flex-col">
                        {project.description && (
                          <p className="text-sm text-zinc-300 line-clamp-2">
                            {project.description}
                          </p>
                        )}

                        {/* Progress */}
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span className="text-zinc-400">Progress</span>
                            <span className="text-white font-medium">
                              {getProgressPercentage(project.stats)}%
                            </span>
                          </div>
                          <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-500 ease-out"
                              style={{
                                width: `${getProgressPercentage(project.stats)}%`,
                                backgroundColor: project.color,
                              }}
                            />
                          </div>
                        </div>

                        {/* Stats */}
                        <div className="grid grid-cols-3 gap-4 pt-2">
                          <div className="text-center">
                            <div className="flex items-center justify-center text-white mb-1">
                              <Calendar className="h-4 w-4 mr-1 text-indigo-400" />
                            </div>
                            <div className="text-lg font-semibold text-white">
                              {project.stats.totalTasks}
                            </div>
                            <div className="text-xs text-zinc-400">Tasks</div>
                          </div>
                          <div className="text-center">
                            <div className="flex items-center justify-center text-white mb-1">
                              <Users className="h-4 w-4 mr-1 text-emerald-400" />
                            </div>
                            <div className="text-lg font-semibold text-white">
                              {project.stats.teamMembers}
                            </div>
                            <div className="text-xs text-zinc-400">Members</div>
                          </div>
                          <div className="text-center">
                            <div className="flex items-center justify-center text-white mb-1">
                              <TrendingUp className="h-4 w-4 mr-1 text-amber-400" />
                            </div>
                            <div className="text-lg font-semibold text-white">
                              {project.stats.recentActivity}
                            </div>
                            <div className="text-xs text-zinc-400">Activity</div>
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="grid grid-cols-4 gap-2 pt-2 mt-auto opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-all duration-300 transform translate-y-0 lg:translate-y-2 lg:group-hover:translate-y-0">
                          <Button
                            variant="ghost"
                            size="sm"
                            aria-label="View Project"
                            className="bg-transparent border border-white/10 text-zinc-400 hover:text-white hover:bg-white/10 hover:border-white/20"
                            onClick={(e) => {
                              e.stopPropagation();
                              router.push(`/projects/${project.id}`);
                            }}
                          >
                            <Eye className="h-4 w-4" aria-hidden="true" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            aria-label="Edit Project"
                            className="bg-transparent border border-white/10 text-zinc-400 hover:text-white hover:bg-white/10 hover:border-white/20"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEditProject(project);
                            }}
                          >
                            <Edit className="h-4 w-4" aria-hidden="true" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            aria-label="Project Settings"
                            className="bg-transparent border border-white/10 text-zinc-400 hover:text-white hover:bg-white/10 hover:border-white/20"
                            onClick={(e) => {
                              e.stopPropagation();
                              router.push(`/projects/${project.id}/settings`);
                            }}
                          >
                            <Settings className="h-4 w-4" aria-hidden="true" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            aria-label="Archive Project"
                            className="bg-transparent border border-white/10 text-zinc-400 hover:text-white hover:bg-white/10 hover:border-white/20"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleArchiveProject(project);
                            }}
                          >
                            <Archive className="h-4 w-4" aria-hidden="true" />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </AnimatePresence>
            </motion.div>

            {/* Empty State */}
            {filteredProjects.length === 0 && !loading && dataFetched && (
              <div className="text-center py-12">
                <div className="mx-auto h-12 w-12 rounded-full bg-white/5 flex items-center justify-center mb-4">
                  <Search className="h-6 w-6 text-zinc-400" />
                </div>
                <h3 className="text-lg font-medium text-white mb-2">No projects found</h3>
                <p className="text-zinc-400 mb-6">
                  {searchQuery || statusFilter !== "all"
                    ? "Try adjusting your search or filter criteria."
                    : "Get started by creating your first project."}
                </p>
                {!searchQuery && statusFilter === "all" && (
                  <Button
                    onClick={handleCreateProject}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Create New Project
                  </Button>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="w-full">
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

        {/* New Task Modal */}
        <NewTaskModal
          isOpen={isNewTaskModalOpen}
          onClose={() => setIsNewTaskModalOpen(false)}
          onTaskCreated={() => {
            taskListRef.current?.refresh();
            setIsNewTaskModalOpen(false);
          }}
        />
      </div>
    </ProtectedLayout >
  );
}