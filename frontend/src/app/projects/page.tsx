"use client";

import { useState, useEffect } from "react";
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
  Edit
} from "lucide-react";
import { Project, ProjectStatus } from "@/types";
import type { CreateProjectRequest, UpdateProjectRequest } from "@/types";
import { ProjectModal } from "@/components/modals/ProjectModal";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";

// Colors for projects
const PROJECT_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

// API functions
const fetchProjects = async (): Promise<Project[]> => {
  const accessToken = localStorage.getItem('accessToken');
  const access_token = localStorage.getItem('access_token');
  const token = accessToken || access_token;
  
  console.log('📁 Projects API: Token check');
  console.log('   accessToken:', accessToken ? `${accessToken.substring(0, 20)}...` : 'MISSING');
  console.log('   access_token:', access_token ? `${access_token.substring(0, 20)}...` : 'MISSING');
  console.log('   Using token:', token ? `${token.substring(0, 20)}...` : 'NO TOKEN');
  
  if (!token) throw new Error('Authentication required. Please login again.');

  const response = await fetch('http://localhost:8000/projects', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  console.log('📁 Projects API: Response received');
  console.log('   Status:', response.status);
  console.log('   Headers:', Object.fromEntries(response.headers.entries()));

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
      window.location.href = '/auth/login';
      throw new Error('Session expired. Please login again.');
    }
    throw new Error(`Failed to fetch projects: ${response.statusText}`);
  }

  const projects = await response.json();
  
  // Convert backend response to frontend format
  return projects.map((project: any, index: number) => ({
    id: project.id,
    name: project.name,
    description: project.description,
    color: PROJECT_COLORS[index % PROJECT_COLORS.length],
    status: project.is_active ? ProjectStatus.ACTIVE : ProjectStatus.ARCHIVED,
    ownerId: project.owner_id,
    owner: {
      id: project.owner_id,
      email: "unknown@company.com",
      username: "unknownuser",
      firstName: "Unknown",
      lastName: "User",
      role: "member" as any,
      isActive: true,
      emailVerified: true,
      createdAt: project.created_at,
      updatedAt: project.updated_at
    },
    members: project.member_summaries || [],
    stats: {
      totalTasks: project.task_count || 0,
      completedTasks: project.completed_tasks || 0,
      inProgressTasks: Math.floor((project.task_count || 0) * 0.3),
      overdueTasks: 0,
      teamMembers: project.member_count || 0,
      recentActivity: 0
    },
    settings: {
      allowPublicAccess: false,
      requireApproval: true,
      defaultTaskVisibility: "team",
      notificationSettings: {
        taskAssigned: true,
        statusChanged: true,
        deadlineApproaching: true,
        commentAdded: true
      }
    },
    createdAt: project.created_at,
    updatedAt: project.updated_at
  }));
};

const createProject = async (projectData: CreateProjectRequest): Promise<Project> => {
  const token = localStorage.getItem('accessToken') || localStorage.getItem('access_token');
  if (!token) throw new Error('No access token found');

  const response = await fetch('http://localhost:8000/projects', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      name: projectData.name,
      description: projectData.description,
      color: projectData.color || PROJECT_COLORS[0],
      memberIds: projectData.memberIds || [],
      settings: projectData.settings
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to create project: ${response.statusText}`);
  }

  const project = await response.json();
  return {
    id: project.id,
    name: project.name,
    description: project.description,
    color: projectData.color || PROJECT_COLORS[0],
    status: ProjectStatus.ACTIVE,
    ownerId: project.owner_id,
    owner: {
      id: project.owner_id,
      email: "current@company.com",
      username: "currentuser",
      firstName: "Current",
      lastName: "User",
      role: "admin" as any,
      isActive: true,
      emailVerified: true,
      createdAt: project.created_at,
      updatedAt: project.updated_at
    },
    members: [],
    stats: {
      totalTasks: 0,
      completedTasks: 0,
      inProgressTasks: 0,
      overdueTasks: 0,
      teamMembers: 1,
      recentActivity: 0
    },
    settings: {
      allowPublicAccess: false,
      requireApproval: true,
      defaultTaskVisibility: "team",
      notificationSettings: {
        taskAssigned: true,
        statusChanged: true,
        deadlineApproaching: true,
        commentAdded: true
      }
    },
    createdAt: project.created_at,
    updatedAt: project.updated_at
  };
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<ProjectStatus | "all">("all");
  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchProjects();
      setProjects(data);
    } catch (err) {
      console.error('Error loading projects:', err);
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  const filteredProjects = projects.filter(project => {
    const matchesSearch = project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         project.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || project.status === statusFilter;
    return matchesSearch && matchesStatus;
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
    if (stats.totalTasks === 0) return 0;
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

  const handleProjectSubmit = async (data: CreateProjectRequest | UpdateProjectRequest) => {
    try {
      if (modalMode === "create") {
        const newProject = await createProject(data as CreateProjectRequest);
        setProjects(prev => [...prev, newProject]);
      } else if (editingProject) {
        // TODO: Implement update project API call
        console.log("Update project not implemented yet");
      }
      setIsProjectModalOpen(false);
      setEditingProject(null);
      setError(null); // Clear any previous errors on success
    } catch (error) {
      console.error("Error saving project:", error);
      const errorMessage = error instanceof Error 
        ? error.message 
        : "Failed to save project. Please try again.";
      setError(errorMessage);
    }
  };

  if (loading) {
    return (
      <ProtectedLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-white">Loading projects...</div>
        </div>
      </ProtectedLayout>
    );
  }

  if (error) {
    return (
      <ProtectedLayout>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="text-red-400 text-center">
            <p className="text-lg font-medium">{error}</p>
            <button
              onClick={loadProjects}
              className="mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
            >
              Retry
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
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-white">Projects</h2>
            <p className="mt-1 text-zinc-400">
              Manage and organize your projects in one place.
            </p>
          </div>
          <Button 
            onClick={handleCreateProject}
            className="bg-indigo-600 hover:bg-indigo-500 text-white"
          >
            <Plus className="h-4 w-4 mr-2" />
            New Project
          </Button>
        </div>

        {/* Search and Filter */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
            <Input
              placeholder="Search projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-zinc-400"
            />
          </div>
          <div className="flex gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as ProjectStatus | "all")}
              className="rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-white text-sm"
            >
              <option value="all">All Status</option>
              <option value={ProjectStatus.ACTIVE}>Active</option>
              <option value={ProjectStatus.ARCHIVED}>Archived</option>
              <option value={ProjectStatus.SUSPENDED}>Suspended</option>
            </select>
            <Button variant="outline" size="sm" className="border-white/10 text-white hover:bg-white/5">
              <Filter className="h-4 w-4 mr-2" />
              More Filters
            </Button>
          </div>
        </div>

        {/* Projects Grid */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filteredProjects.map((project) => (
            <Card key={project.id} className="border-white/10 bg-white/5 backdrop-blur-sm hover:bg-white/10 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className="h-10 w-10 rounded-lg flex items-center justify-center shadow-lg"
                      style={{ backgroundColor: project.color }}
                    >
                      <span className="font-bold text-white text-sm">
                        {project.name && typeof project.name === 'string' ? project.name[0] : ''}
                      </span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <CardTitle className="text-white text-lg truncate">
                        {project.name}
                      </CardTitle>
                      <p className="text-sm text-zinc-400 mt-1">
                        by {project.owner.firstName} {project.owner.lastName}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    {getStatusBadge(project.status)}
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-zinc-400 hover:text-white">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              
              <CardContent className="space-y-4">
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
                  <div className="h-2 rounded-full bg-white/10">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${getProgressPercentage(project.stats)}%`,
                        backgroundColor: project.color
                      }}
                    />
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-4 pt-2">
                  <div className="text-center">
                    <div className="flex items-center justify-center text-white mb-1">
                      <Calendar className="h-4 w-4 mr-1" />
                    </div>
                    <div className="text-lg font-semibold text-white">
                      {project.stats.totalTasks}
                    </div>
                    <div className="text-xs text-zinc-400">Tasks</div>
                  </div>
                  <div className="text-center">
                    <div className="flex items-center justify-center text-white mb-1">
                      <Users className="h-4 w-4 mr-1" />
                    </div>
                    <div className="text-lg font-semibold text-white">
                      {project.stats.teamMembers}
                    </div>
                    <div className="text-xs text-zinc-400">Members</div>
                  </div>
                  <div className="text-center">
                    <div className="flex items-center justify-center text-white mb-1">
                      <TrendingUp className="h-4 w-4 mr-1" />
                    </div>
                    <div className="text-lg font-semibold text-white">
                      {project.stats.recentActivity}
                    </div>
                    <div className="text-xs text-zinc-400">Activity</div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2 pt-2">
                  <Button variant="outline" size="sm" className="flex-1 border-white/10 text-white hover:bg-white/5">
                    <Eye className="h-3 w-3 mr-1" />
                    View
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="border-white/10 text-white hover:bg-white/5"
                    onClick={() => handleEditProject(project)}
                  >
                    <Edit className="h-3 w-3" />
                  </Button>
                  <Button variant="outline" size="sm" className="border-white/10 text-white hover:bg-white/5">
                    <Settings className="h-3 w-3" />
                  </Button>
                  <Button variant="outline" size="sm" className="border-white/10 text-white hover:bg-white/5">
                    <Archive className="h-3 w-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Empty State */}
        {filteredProjects.length === 0 && (
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
              <Button className="bg-indigo-600 hover:bg-indigo-500 text-white">
                <Plus className="h-4 w-4 mr-2" />
                Create New Project
              </Button>
            )}
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