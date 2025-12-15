/* eslint-disable @typescript-eslint/no-explicit-any */
// ===========================================
// API Endpoints Mapping - Simplified
// ===========================================

import { apiClient, createDeduplicatedRequest } from "./api-client";
import type {
  User,
  Project,
  Task,
  AuthResponse,
  LoginRequest,
  RegisterRequest,
  UpdateUserRequest,
  CreateProjectRequest,
  UpdateProjectRequest,
  CreateTaskRequest,
  UpdateTaskRequest,
  Notification,
  RecentActivity,
  InviteUserRequest,
} from "@/types";
import type {
  AnalyticsResponse,
  TeamWorkloadPaginatedResponse,
  TeamWorkloadParams,
} from "@/app/analytics/types";

// ===========================================
// Authentication Endpoints
// ===========================================

export const authApi = {
  // Login
  login: async (credentials: LoginRequest): Promise<AuthResponse> => {
    const { data } = await apiClient.post("/auth/login", credentials);
    return data;
  },

  // Register
  register: async (userData: RegisterRequest): Promise<AuthResponse> => {
    const { data } = await apiClient.post("/auth/register", userData);
    return data;
  },

  // Logout
  logout: async (): Promise<void> => {
    await apiClient.post("/auth/logout");
  },

  // Refresh token
  refreshToken: async (refreshToken: string): Promise<AuthResponse> => {
    const { data } = await apiClient.post(
      "/auth/refresh",
      {},
      {
        headers: {
          Authorization: `Bearer ${refreshToken}`,
        },
      },
    );
    return data;
  },

  // Get current user profile with deduplication
  getCurrentUser: async (): Promise<User> => {
    // Log entry and stack to help find duplicate callers
    if (process.env.NODE_ENV === "development") {
      // Empty block intentionally - used for debugging when needed
    }

    const cacheKey = "auth-getCurrentUser";

    return createDeduplicatedRequest(async () => {
      try {
        const { data } = await apiClient.get("/auth/me");
        return data;
      } catch (err: unknown) {
        // If cookie-based request fails (401), try Authorization header fallback using stored token
        const status = (err as any)?.response?.status;
        if (status === 401) {
          // Check if we have a token before retrying
          const token =
            typeof window !== "undefined"
              ? (localStorage.getItem("access_token") ??
                localStorage.getItem("accessToken"))
              : null;

          if (!token) {
            throw err; // No token, don't retry
          }

          try {
            const { API_CONFIG } = await import("@/lib/constants");

            // Use direct axios call to avoid interceptor side effects
            const axios = (await import("axios")).default;
            const resp = await axios.get(`${API_CONFIG.BASE_URL}/auth/me`, {
              headers: { Authorization: `Bearer ${token}` },
              withCredentials: false, // Bearer token flow, not cookies
            });
            return resp.data;
          } catch (_fallbackErr) {
            // fall through to throw original error
          }
        }
        throw err;
      }
    }, cacheKey);
  },

  // Change password
  changePassword: async (
    currentPassword: string,
    newPassword: string,
  ): Promise<void> => {
    try {
      const response = await apiClient.post("/auth/change-password", {
        currentPassword,
        newPassword,
      });
      console.log("API: Change password response:", response.data);
      return response.data;
    } catch (error: any) {
      console.error("API: Change password error:", error);
      throw error;
    }
  },

  // Forgot password
  forgotPassword: async (email: string): Promise<any> => {
    try {
      const response = await apiClient.post("/auth/forgot-password", { email });

      return response.data;
    } catch (error: any) {
      console.error("API: Forgot password error:", error);
      throw error;
    }
  },

  // Reset password
  resetPassword: async (token: string, newPassword: string): Promise<any> => {
    try {
      const response = await apiClient.post("/auth/reset-password", {
        token,
        new_password: newPassword,
      });

      return response.data;
    } catch (error: any) {
      console.error("API: Reset password error:", error);
      throw error;
    }
  },

  // Validate reset token
  validateResetToken: async (token: string): Promise<any> => {
    try {
      const response = await apiClient.post("/auth/validate-reset-token", {
        token,
      });

      return response.data;
    } catch (error: any) {
      console.error("API: Validate reset token error:", error);
      throw error;
    }
  },
};

// ===========================================
// File Management Endpoints
// ===========================================

export const fileApi = {
  // Upload file
  uploadFile: async (formData: FormData): Promise<unknown> => {
    const { data } = await apiClient.post("/files/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  // Delete file
  deleteFile: async (url: string): Promise<void> => {
    await apiClient.delete("/files/delete", { data: { url } });
  },

  // Get file info
  getFileInfo: async (url: string): Promise<unknown> => {
    const { data } = await apiClient.get("/files/info", { params: { url } });
    return data;
  },
};

// ===========================================
// Task Management Endpoints
// ===========================================

export const tasksApi = {
  // Get all tasks for user
  getTasks: async (
    skip = 0,
    limit = 100,
    search?: string,
    status?: string,
  ): Promise<Task[]> => {
    const cacheKey = `tasks-getTasks-${skip}-${limit}-${search}-${status}`;
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/tasks/", {
        params: { skip, limit, search, status },
      });
      return data;
    }, cacheKey);
  },

  // Get user's tasks
  getMyTasks: async (
    skip = 0,
    limit = 100,
    search?: string,
    status?: string,
  ): Promise<Task[]> => {
    const cacheKey = `tasks-getMyTasks-${skip}-${limit}-${search}-${status}`;
    return createDeduplicatedRequest(async () => {
      const params: any = { skip, limit };
      if (search) {
        params.search = search;
      }
      if (status && status !== "all") {
        params.status = status;
      }
      const { data } = await apiClient.get("/tasks/my/tasks", { params });
      return data;
    }, cacheKey);
  },

  // Get task by ID
  getTask: async (taskId: string): Promise<Task> => {
    const cacheKey = `tasks-getTask-${taskId}`;
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get(`/tasks/${taskId}`);
      return data;
    }, cacheKey);
  },

  // Get tasks for a project
  getProjectTasks: async (
    projectId: string,
    skip = 0,
    limit = 100,
    sortBy?: string,
    sortOrder?: string,
    search?: string,
    statusFilter?: string,
  ): Promise<Task[]> => {
    const cacheKey = `tasks-getProjectTasks-${projectId}-${skip}-${limit}-${sortBy}-${sortOrder}-${search}-${statusFilter}`;
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get(`/projects/${projectId}/tasks`, {
        params: {
          skip,
          limit,
          sort_by: sortBy,
          sort_order: sortOrder,
          search,
          status: statusFilter,
        },
      });
      return data;
    }, cacheKey);
  },

  // Create task for a project
  createTask: async (
    projectId: string,
    taskData: CreateTaskRequest,
  ): Promise<Task> => {
    const { data } = await apiClient.post(
      `/projects/${projectId}/tasks`,
      taskData,
    );
    return data;
  },

  // Update task
  updateTask: async (
    taskId: string,
    taskData: UpdateTaskRequest,
  ): Promise<Task> => {
    const { data } = await apiClient.put(`/tasks/${taskId}`, taskData);
    return data;
  },

  // Update project task
  updateProjectTask: async (
    projectId: string,
    taskId: string,
    taskData: UpdateTaskRequest,
  ): Promise<Task> => {
    const { data } = await apiClient.put(
      `/projects/${projectId}/tasks/${taskId}`,
      taskData,
    );
    return data;
  },

  // Delete task
  deleteTask: async (taskId: string): Promise<void> => {
    await apiClient.delete(`/tasks/${taskId}`);
  },

  // Delete project task
  deleteProjectTask: async (
    projectId: string,
    taskId: string,
  ): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}/tasks/${taskId}`);
  },

  // Update task status
  updateTaskStatus: async (taskId: string, status: string): Promise<Task> => {
    const { data } = await apiClient.put(`/tasks/${taskId}/status`, { status });
    return data;
  },

  // Update project task status
  updateProjectTaskStatus: async (
    projectId: string,
    taskId: string,
    status: string,
  ): Promise<Task> => {
    const { data } = await apiClient.put(
      `/projects/${projectId}/tasks/${taskId}/status`,
      { status },
    );
    return data;
  },

  // Assign task
  assignTask: async (taskId: string, assigneeId: string): Promise<Task> => {
    const { data } = await apiClient.put(`/tasks/${taskId}/assign`, {
      assignee_id: assigneeId,
    });
    return data;
  },

  // Assign project task
  assignProjectTask: async (
    projectId: string,
    taskId: string,
    assigneeId: string,
  ): Promise<Task> => {
    const { data } = await apiClient.put(
      `/projects/${projectId}/tasks/${taskId}/assign`,
      { assignee_id: assigneeId },
    );
    return data;
  },
};

// ===========================================
// Project Management Endpoints
// ===========================================

export const projectsApi = {
  // Get all projects with deduplication
  getProjects: async (
    skip = 0,
    limit = 100,
    userProjectsOnly = false,
  ): Promise<Project[]> => {
    const cacheKey = `projects-getProjects-${skip}-${limit}-${userProjectsOnly}`;

    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/projects", {
        params: { skip, limit, user_projects_only: userProjectsOnly },
      });

      return data;
    }, cacheKey);
  },

  // Get project by ID
  getProject: async (projectId: string): Promise<Project> => {
    const cacheKey = `projects-getProject-${projectId}`;
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get(`/projects/${projectId}`);
      return data;
    }, cacheKey);
  },

  // Create project
  createProject: async (
    projectData: CreateProjectRequest,
  ): Promise<Project> => {
    const { data } = await apiClient.post("/projects", projectData);
    return data;
  },

  // Update project
  updateProject: async (
    projectId: string,
    projectData: UpdateProjectRequest,
  ): Promise<Project> => {
    const { data } = await apiClient.put(`/projects/${projectId}`, projectData);
    return data;
  },

  // Delete project
  deleteProject: async (projectId: string): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}`);
  },

  // Get project members
  getProjectMembers: async (projectId: string): Promise<unknown[]> => {
    const cacheKey = `projects-getProjectMembers-${projectId}`;
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get(`/projects/${projectId}/members`);
      return data;
    }, cacheKey);
  },

  // Add project member
  addProjectMember: async (
    projectId: string,
    memberData: unknown,
  ): Promise<unknown> => {
    const { data } = await apiClient.post(
      `/projects/${projectId}/members`,
      memberData,
    );
    return data;
  },

  // Remove project member
  removeProjectMember: async (
    projectId: string,
    memberUserId: string,
  ): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}/members/${memberUserId}`);
  },

  // Update member role
  updateMemberRole: async (
    projectId: string,
    memberUserId: string,
    role: string,
  ): Promise<unknown> => {
    const { data } = await apiClient.put(
      `/projects/${projectId}/members/${memberUserId}/role`,
      { role },
    );
    return data;
  },
};

// ===========================================
// User Management Endpoints
// ===========================================

export const usersApi = {
  // Get current user profile
  getCurrentUser: async (): Promise<User> => {
    const cacheKey = "users-getCurrentUser";
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/users/me");
      return data;
    }, cacheKey);
  },

  // Update current user profile
  updateCurrentUser: async (userData: UpdateUserRequest): Promise<User> => {
    const { data } = await apiClient.put("/users/me", userData);
    return data;
  },

  // Upload user avatar
  uploadAvatar: async (formData: FormData): Promise<User> => {
    const { data } = await apiClient.post("/users/me/avatar", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  // Search user by email
  searchUserByEmail: async (email: string): Promise<User> => {
    const cacheKey = `users-searchUserByEmail-${email}`;
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get(`/users/search/${email}`);
      return data;
    }, cacheKey);
  },

  // Search users
  searchUsers: async (
    query: string,
    skip = 0,
    limit = 20,
    role?: string,
    status?: string,
  ): Promise<User[]> => {
    const cacheKey = `users-searchUsers-${query}-${skip}-${limit}-${role}-${status}`;
    return createDeduplicatedRequest(async () => {
      const params: any = { q: query, skip, limit };
      if (role && role !== "all") {
        params.role = role;
      }
      if (status && status !== "all") {
        params.status = status;
      }

      const { data } = await apiClient.get("/users/search", { params });
      return data;
    }, cacheKey);
  },

  // Get user settings
  getSettings: async (): Promise<any> => {
    const cacheKey = "users-getSettings";
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/users/me/settings");
      return data;
    }, cacheKey);
  },

  // Update user settings
  updateSettings: async (settingsData: any): Promise<any> => {
    const { data } = await apiClient.patch("/users/me/settings", settingsData);
    return data;
  },

  // Invite user
  inviteUser: async (userData: InviteUserRequest): Promise<User> => {
    const { data } = await apiClient.post("/users/invite", userData);
    return data;
  },

  // Get user stats
  getStats: async (): Promise<any> => {
    const cacheKey = "users-getStats";
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/users/stats");
      return data;
    }, cacheKey);
  },
};

// ===========================================
// Dashboard Endpoints - Simplified
// ===========================================

export const dashboardApi = {
  // Get dashboard overview
  getOverview: async (): Promise<{
    stats: {
      totalProjects: number;
      totalProjectsChange?: string;
      totalProjectsTrend?: "up" | "down";
      totalTasks: number;
      completedTasks: number;
      pendingTasks: number;
      teamMembers: number;
      inProgressTasks?: number;
      inProgressTasksChange?: string;
      inProgressTasksTrend?: "up" | "down";
      pendingReviewTasks?: number;
      pendingReviewTasksChange?: string;
      pendingReviewTasksTrend?: "up" | "down";
      teamVelocity?: number;
      teamVelocityChange?: string;
      teamVelocityTrend?: "up" | "down";
    };
    recentProjects: Project[];
    recentActivities: RecentActivity[];
    upcomingDeadlines: unknown[];
    charts: unknown[];
  }> => {
    const { data } = await apiClient.get("/dashboard/overview");
    return data;
  },

  // Get user's tasks for today
  getTodayTasks: async (): Promise<Task[]> => {
    const cacheKey = "dashboard-getTodayTasks";
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/dashboard/today-tasks");
      return data;
    }, cacheKey);
  },

  // Get recent projects
  getRecentProjects: async (): Promise<Project[]> => {
    const cacheKey = "dashboard-getRecentProjects";
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/dashboard/recent-projects");
      return data;
    }, cacheKey);
  },

  // Get team activity
  getTeamActivity: async (): Promise<unknown[]> => {
    const cacheKey = "dashboard-getTeamActivity";
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/dashboard/team-activity");
      return data;
    }, cacheKey);
  },
};

// ===========================================
// Analytics Endpoints
// ===========================================

export const analyticsApi = {
  // Get analytics overview
  getAnalytics: async (period: string): Promise<AnalyticsResponse> => {
    const cacheKey = `analytics-getAnalytics-${period}`;
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/analytics/overview", {
        params: { period },
      });
      return data;
    }, cacheKey);
  },

  // Get paginated team workload (scalable for 1K-100K users)
  getTeamWorkload: async (
    params: TeamWorkloadParams,
  ): Promise<TeamWorkloadPaginatedResponse> => {
    const { data } = await apiClient.get("/analytics/team-workload", {
      params: {
        page: params.page ?? 1,
        page_size: params.pageSize ?? 10,
        search: params.search ?? undefined,
        sort_by: params.sortBy ?? "tasks",
        sort_order: params.sortOrder ?? "desc",
      },
    });
    return data;
  },
};

// ===========================================
// Notification Endpoints
// ===========================================

export const notificationsApi = {
  // Get all notifications
  getNotifications: async (skip = 0, limit = 50): Promise<Notification[]> => {
    const cacheKey = `notifications-getNotifications-${skip}-${limit}`;
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/notifications", {
        params: { skip, limit },
      });
      return data;
    }, cacheKey);
  },

  // Get unread count
  getUnreadCount: async (): Promise<number> => {
    const cacheKey = "notifications-getUnreadCount";
    return createDeduplicatedRequest(
      async () => {
        const { data } = await apiClient.get("/notifications/unread-count");
        return data;
      },
      cacheKey,
      5000000,
    ); // เพิ่มเวลาเป็น 5 นาที (300,000ms)
  },

  // Mark as read
  markAsRead: async (notificationId: string): Promise<Notification> => {
    const { data } = await apiClient.put(
      `/notifications/${notificationId}/read`,
    );
    return data;
  },

  // Mark all as read
  markAllAsRead: async (): Promise<Notification[]> => {
    const { data } = await apiClient.put("/notifications/read-all");
    return data;
  },

  // Delete notification
  deleteNotification: async (notificationId: string): Promise<void> => {
    await apiClient.delete(`/notifications/${notificationId}`);
  },
};
